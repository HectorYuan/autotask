"""
Workflow 预留接口
v1 阶段：定义接口规范，为未来扩展预留空间
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import uuid
from datetime import datetime

from autotask.core.state_machine import StateMachine, State, Transition


class WorkflowStatus(str, Enum):
    """工作流状态"""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """步骤类型"""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    SUBWORKFLOW = "subworkflow"
    AWAIT = "await"


@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    step_type: StepType = StepType.TASK
    config: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)  # 下一步骤 ID 列表
    on_error: Optional[str] = None  # 错误处理步骤 ID
    retry_count: int = 0
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowContext:
    """工作流执行上下文"""
    workflow_id: str
    execution_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set_variable(self, key: str, value: Any) -> None:
        """设置变量"""
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)


class WorkflowStepHandler(ABC):
    """
    工作流步骤处理器接口
    
    各步骤类型需实现此接口
    """
    
    @property
    @abstractmethod
    def step_type(self) -> StepType:
        """步骤类型"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> StepResult:
        """
        执行步骤
        
        Args:
            step: 步骤定义
            context: 工作流上下文
            
        Returns:
            步骤执行结果
        """
        pass
    
    @abstractmethod
    def validate(self, step: WorkflowStep) -> bool:
        """
        验证步骤配置
        
        Args:
            step: 步骤定义
            
        Returns:
            是否有效
        """
        pass


class Workflow(ABC):
    """
    工作流基类
    
    定义工作流接口规范
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        version: str = "1.0",
    ):
        self.id = id
        self.name = name
        self.version = version
        self._steps: Dict[str, WorkflowStep] = {}
        self._entry_step_id: Optional[str] = None
        self._step_handlers: Dict[StepType, WorkflowStepHandler] = {}
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowContext:
        """
        执行工作流
        
        Args:
            input_data: 输入数据
            
        Returns:
            工作流执行上下文
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        验证工作流定义
        
        Returns:
            是否有效
        """
        pass
    
    def add_step(self, step: WorkflowStep) -> None:
        """添加步骤"""
        self._steps[step.id] = step
    
    def remove_step(self, step_id: str) -> None:
        """移除步骤"""
        if step_id in self._steps:
            del self._steps[step_id]
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """获取步骤"""
        return self._steps.get(step_id)
    
    def list_steps(self) -> List[WorkflowStep]:
        """列出所有步骤"""
        return list(self._steps.values())
    
    def set_entry_step(self, step_id: str) -> None:
        """设置入口步骤"""
        self._entry_step_id = step_id
    
    def get_entry_step(self) -> Optional[WorkflowStep]:
        """获取入口步骤"""
        if self._entry_step_id:
            return self._steps.get(self._entry_step_id)
        return None
    
    def register_handler(self, handler: WorkflowStepHandler) -> None:
        """注册步骤处理器"""
        self._step_handlers[handler.step_type] = handler
    
    def get_handler(self, step_type: StepType) -> Optional[WorkflowStepHandler]:
        """获取步骤处理器"""
        return self._step_handlers.get(step_type)


class WorkflowBuilder:
    """
    工作流构建器
    
    用于以 fluent 方式构建工作流
    """
    
    def __init__(self, workflow: Workflow):
        self._workflow = workflow
        self._current_step: Optional[WorkflowStep] = None
    
    def add_step(
        self,
        name: str,
        step_type: StepType = StepType.TASK,
        config: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowBuilder":
        """添加步骤"""
        step = WorkflowStep(
            name=name,
            step_type=step_type,
            config=config or {},
        )
        self._workflow.add_step(step)
        self._current_step = step
        return self
    
    def then(self, name: str, step_type: StepType = StepType.TASK) -> "WorkflowBuilder":
        """添加下一步骤"""
        step = WorkflowStep(
            name=name,
            step_type=step_type,
        )
        self._workflow.add_step(step)
        if self._current_step:
            self._current_step.next_steps.append(step.id)
        self._current_step = step
        return self
    
    def on_error(self, step_id: str) -> "WorkflowBuilder":
        """设置错误处理步骤"""
        if self._current_step:
            self._current_step.on_error = step_id
        return self
    
    def retry(self, count: int) -> "WorkflowBuilder":
        """设置重试次数"""
        if self._current_step:
            self._current_step.retry_count = count
        return self
    
    def timeout(self, seconds: int) -> "WorkflowBuilder":
        """设置超时时间"""
        if self._current_step:
            self._current_step.timeout = seconds
        return self
    
    def build(self) -> Workflow:
        """构建工作流"""
        return self._workflow


# v1 预留：简单的线性工作流实现
class LinearWorkflow(Workflow):
    """
    线性工作流
    
    简单的顺序执行工作流
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        version: str = "1.0",
    ):
        super().__init__(id, name, version)
        self._status = WorkflowStatus.DRAFT
    
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowContext:
        """执行工作流"""
        context = WorkflowContext(
            workflow_id=self.id,
            execution_id=str(uuid.uuid4()),
            input_data=input_data,
        )
        
        self._status = WorkflowStatus.RUNNING
        
        try:
            current_step = self.get_entry_step()
            while current_step:
                handler = self.get_handler(current_step.step_type)
                if handler:
                    result = await handler.execute(current_step, context)
                    context.step_results[current_step.id] = result
                    
                    if not result.success:
                        if current_step.on_error:
                            current_step = self.get_step(current_step.on_error)
                        else:
                            self._status = WorkflowStatus.FAILED
                            break
                    else:
                        # 获取下一步
                        if current_step.next_steps:
                            current_step = self.get_step(current_step.next_steps[0])
                        else:
                            current_step = None
                else:
                    break
            
            if current_step is None and self._status == WorkflowStatus.RUNNING:
                self._status = WorkflowStatus.COMPLETED
        
        except Exception as e:
            self._status = WorkflowStatus.FAILED
        
        return context
    
    def validate(self) -> bool:
        """验证工作流"""
        if not self._entry_step_id:
            return False
        if not self._steps:
            return False
        return True
