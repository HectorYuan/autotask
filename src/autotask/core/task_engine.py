"""
任务引擎
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from autotask.core.state_machine import TaskStateMachine, State
from autotask.core.executor import ExecutionContext, ExecutionResult
from autotask.core.executor_factory import ExecutorFactory, ExecutorType
from autotask.core.event_bus import EventBus, Event


@dataclass
class Task:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    executor_type: ExecutorType = ExecutorType.MAIN_AGENT
    input_data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: State
    result: Optional[ExecutionResult] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskEngine:
    """
    任务引擎
    
    职责：
    - 任务生命周期管理
    - 任务调度执行
    - 状态转换控制
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._tasks: Dict[str, Task] = {}
        self._task_states: Dict[str, TaskStateMachine] = {}
        self._task_results: Dict[str, TaskResult] = {}
        self._event_bus = event_bus or EventBus()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._max_concurrent = 5
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
    
    async def submit(self, task: Task) -> str:
        """
        提交任务
        
        Args:
            task: 任务对象
            
        Returns:
            任务 ID
        """
        self._tasks[task.id] = task
        self._task_states[task.id] = TaskStateMachine()
        self._task_results[task.id] = TaskResult(
            task_id=task.id,
            status=State.PENDING,
        )
        
        # 发布任务创建事件
        await self._event_bus.publish(Event(
            type="task.created",
            data={"task_id": task.id, "task": task},
        ))
        
        return task.id
    
    async def run(self, task_id: str) -> TaskResult:
        """
        运行任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务结果
        """
        if task_id not in self._tasks:
            raise ValueError(f"任务不存在: {task_id}")
        
        task = self._tasks[task_id]
        state_machine = self._task_states[task_id]
        
        # 检查是否可启动
        if not state_machine.can_transition("start"):
            return self._task_results[task_id]
        
        async with self._semaphore:
            # 状态转换
            state_machine.start()
            self._task_results[task_id].status = State.RUNNING
            self._task_results[task_id].started_at = datetime.now()
            
            # 发布任务开始事件
            await self._event_bus.publish(Event(
                type="task.started",
                data={"task_id": task_id},
            ))
            
            try:
                # 创建执行器
                executor = ExecutorFactory.create(task.executor_type)
                context = ExecutionContext(
                    task_id=task_id,
                    task_data=task.input_data,
                )
                
                # 执行任务
                result = await executor.run(context)
                
                # 处理结果
                if result.success:
                    state_machine.complete()
                    self._task_results[task_id].status = State.COMPLETED
                else:
                    state_machine.fail()
                    self._task_results[task_id].status = State.FAILED
                    self._task_results[task_id].error = result.error
                
                self._task_results[task_id].result = result
                
            except Exception as e:
                state_machine.fail()
                self._task_results[task_id].status = State.FAILED
                self._task_results[task_id].error = str(e)
            
            finally:
                self._task_results[task_id].completed_at = datetime.now()
                
                # 发布任务完成事件
                await self._event_bus.publish(Event(
                    type="task.completed",
                    data={"task_id": task_id, "result": self._task_results[task_id]},
                ))
        
        return self._task_results[task_id]
    
    async def cancel(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功取消
        """
        if task_id not in self._task_states:
            return False
        
        state_machine = self._task_states[task_id]
        if state_machine.transition("cancel"):
            self._task_results[task_id].status = State.CANCELLED
            await self._event_bus.publish(Event(
                type="task.cancelled",
                data={"task_id": task_id},
            ))
            return True
        return False
    
    def get_status(self, task_id: str) -> Optional[State]:
        """获取任务状态"""
        if task_id in self._task_states:
            return self._task_states[task_id].current_state
        return None
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self._task_results.get(task_id)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务对象"""
        return self._tasks.get(task_id)
    
    def list_tasks(self, status: Optional[State] = None) -> List[Task]:
        """列出任务"""
        if status is None:
            return list(self._tasks.values())
        return [
            task for task_id, task in self._tasks.items()
            if self._task_states[task_id].current_state == status
        ]
