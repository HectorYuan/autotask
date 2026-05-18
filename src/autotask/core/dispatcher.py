"""
任务分发器
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from autotask.core.task_engine import Task, TaskEngine, TaskResult
from autotask.core.executor_factory import ExecutorType


class DispatchStrategy(str, Enum):
    """分发策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    HASH = "hash"


@dataclass
class Worker:
    """工作节点"""
    id: str
    name: str
    executor_types: List[ExecutorType]
    max_concurrent: int = 5
    current_load: int = 0
    available: bool = True


@dataclass
class DispatchResult:
    """分发结果"""
    task_id: str
    worker_id: Optional[str]
    success: bool
    message: str = ""


class TaskDispatcher:
    """
    任务分发器
    
    职责：
    - 管理工作节点
    - 根据策略分发任务
    - 负载均衡
    """
    
    def __init__(self, task_engine: TaskEngine):
        self._task_engine = task_engine
        self._workers: Dict[str, Worker] = {}
        self._strategy = DispatchStrategy.ROUND_ROBIN
        self._round_robin_index = 0
        self._dispatch_callbacks: List[Callable[[str, str], None]] = []
    
    def add_worker(self, worker: Worker) -> None:
        """添加工作节点"""
        self._workers[worker.id] = worker
    
    def remove_worker(self, worker_id: str) -> None:
        """移除工作节点"""
        if worker_id in self._workers:
            del self._workers[worker_id]
    
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """获取工作节点"""
        return self._workers.get(worker_id)
    
    def list_workers(self, available_only: bool = False) -> List[Worker]:
        """列出工作节点"""
        workers = list(self._workers.values())
        if available_only:
            workers = [w for w in workers if w.available]
        return workers
    
    def set_strategy(self, strategy: DispatchStrategy) -> None:
        """设置分发策略"""
        self._strategy = strategy
    
    def on_dispatch(self, callback: Callable[[str, str], None]) -> None:
        """注册分发回调"""
        self._dispatch_callbacks.append(callback)
    
    async def dispatch(self, task: Task) -> DispatchResult:
        """
        分发任务到工作节点
        
        Args:
            task: 任务对象
            
        Returns:
            分发结果
        """
        # 选择工作节点
        worker = self._select_worker(task)
        
        if worker is None:
            return DispatchResult(
                task_id=task.id,
                worker_id=None,
                success=False,
                message="没有可用工作节点",
            )
        
        # 更新负载
        worker.current_load += 1
        
        # 提交任务
        await self._task_engine.submit(task)
        
        # 触发回调
        for callback in self._dispatch_callbacks:
            callback(task.id, worker.id)
        
        return DispatchResult(
            task_id=task.id,
            worker_id=worker.id,
            success=True,
            message=f"分发到 {worker.name}",
        )
    
    def _select_worker(self, task: Task) -> Optional[Worker]:
        """
        根据策略选择工作节点
        
        Args:
            task: 任务对象
            
        Returns:
            选中的工作节点
        """
        # 过滤支持该任务类型的节点
        candidates = [
            w for w in self._workers.values()
            if w.available
            and w.current_load < w.max_concurrent
            and task.executor_type in w.executor_types
        ]
        
        if not candidates:
            return None
        
        # 根据策略选择
        if self._strategy == DispatchStrategy.ROUND_ROBIN:
            return self._round_robin_select(candidates)
        elif self._strategy == DispatchStrategy.LEAST_LOADED:
            return min(candidates, key=lambda w: w.current_load)
        elif self._strategy == DispatchStrategy.RANDOM:
            import random
            return random.choice(candidates)
        elif self._strategy == DispatchStrategy.HASH:
            return self._hash_select(candidates, task.id)
        
        return candidates[0]
    
    def _round_robin_select(self, candidates: List[Worker]) -> Worker:
        """轮询选择"""
        worker = candidates[self._round_robin_index % len(candidates)]
        self._round_robin_index += 1
        return worker
    
    def _hash_select(self, candidates: List[Worker], task_id: str) -> Worker:
        """哈希选择"""
        hash_value = int(hashlib.md5(task_id.encode()).hexdigest(), 16)
        return candidates[hash_value % len(candidates)]
    
    def update_worker_load(self, worker_id: str, delta: int) -> None:
        """更新工作节点负载"""
        if worker_id in self._workers:
            self._workers[worker_id].current_load += delta
    
    def set_worker_available(self, worker_id: str, available: bool) -> None:
        """设置工作节点可用性"""
        if worker_id in self._workers:
            self._workers[worker_id].available = available
