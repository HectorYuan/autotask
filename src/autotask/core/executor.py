"""
执行器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from enum import Enum
import asyncio
import time


class ExecutorStatus(str, Enum):
    """执行器状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class ExecutionContext:
    """执行上下文"""
    task_id: str
    task_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self.metadata.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置上下文值"""
        self.metadata[key] = value


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def failed(self) -> bool:
        return not self.success
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "steps": self.steps,
            "metadata": self.metadata,
        }


class Executor(ABC):
    """
    执行器基类
    
    职责：
    - 执行具体任务逻辑
    - 管理执行状态
    - 报告执行结果
    """
    
    def __init__(self):
        self._status = ExecutorStatus.IDLE
        self._current_context: Optional[ExecutionContext] = None
    
    @property
    def status(self) -> ExecutorStatus:
        """获取执行器状态"""
        return self._status
    
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        执行任务
        
        Args:
            context: 执行上下文
            
        Returns:
            执行结果
        """
        pass
    
    @abstractmethod
    def validate_input(self, context: ExecutionContext) -> bool:
        """
        验证输入
        
        Args:
            context: 执行上下文
            
        Returns:
            验证是否通过
        """
        pass
    
    async def run(self, context: ExecutionContext) -> ExecutionResult:
        """
        运行执行器
        
        包含验证、执行、状态管理
        """
        # 状态检查
        if self._status == ExecutorStatus.STOPPED:
            return ExecutionResult(
                success=False,
                error="执行器已停止",
            )
        
        # 输入验证
        if not self.validate_input(context):
            return ExecutionResult(
                success=False,
                error="输入验证失败",
            )
        
        # 更新状态
        self._status = ExecutorStatus.RUNNING
        self._current_context = context
        
        start_time = time.time()
        
        try:
            # 执行任务
            result = await self.execute(context)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
        finally:
            self._status = ExecutorStatus.IDLE
            self._current_context = None
    
    def pause(self) -> None:
        """暂停执行器"""
        if self._status == ExecutorStatus.RUNNING:
            self._status = ExecutorStatus.PAUSED
    
    def resume(self) -> None:
        """恢复执行器"""
        if self._status == ExecutorStatus.PAUSED:
            self._status = ExecutorStatus.RUNNING
    
    def stop(self) -> None:
        """停止执行器"""
        self._status = ExecutorStatus.STOPPED


class MainAgentExecutor(Executor):
    """主 Agent 执行器"""
    
    def validate_input(self, context: ExecutionContext) -> bool:
        return "task" in context.task_data
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        # 模拟主 Agent 执行逻辑
        await asyncio.sleep(0.1)
        return ExecutionResult(
            success=True,
            output={"message": "主 Agent 执行完成"},
        )


class SubAgentExecutor(Executor):
    """子 Agent 执行器"""
    
    def validate_input(self, context: ExecutionContext) -> bool:
        return "sub_task" in context.task_data
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        await asyncio.sleep(0.1)
        return ExecutionResult(
            success=True,
            output={"message": "子 Agent 执行完成"},
        )


class ScriptExecutor(Executor):
    """脚本执行器"""
    
    def validate_input(self, context: ExecutionContext) -> bool:
        return "script" in context.task_data
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        script = context.task_data["script"]
        await asyncio.sleep(0.1)
        return ExecutionResult(
            success=True,
            output={"executed": script},
        )


class ChainExecutor(Executor):
    """链式执行器"""
    
    def validate_input(self, context: ExecutionContext) -> bool:
        return "chain" in context.task_data
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        chain = context.task_data["chain"]
        results = []
        for step in chain:
            await asyncio.sleep(0.05)
            results.append(step)
        return ExecutionResult(
            success=True,
            output={"chain_results": results},
        )
