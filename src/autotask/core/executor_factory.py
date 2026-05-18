"""
执行器工厂 - 独立实现
"""

from enum import Enum
from typing import Dict, Type
from autotask.core.executor import (
    Executor,
    MainAgentExecutor,
    SubAgentExecutor,
    ScriptExecutor,
    ChainExecutor,
)


class ExecutorType(str, Enum):
    """执行器类型枚举"""
    MAIN_AGENT = "main_agent"
    SUB_AGENT = "sub_agent"
    SCRIPT = "script"
    CHAIN = "chain"
    # 预留扩展
    WORKFLOW = "workflow"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


class ExecutorFactory:
    """
    执行器工厂
    
    职责：
    - 创建各类执行器实例
    - 管理执行器注册表
    """
    
    _executors: Dict[ExecutorType, Type[Executor]] = {
        ExecutorType.MAIN_AGENT: MainAgentExecutor,
        ExecutorType.SUB_AGENT: SubAgentExecutor,
        ExecutorType.SCRIPT: ScriptExecutor,
        ExecutorType.CHAIN: ChainExecutor,
    }
    
    @classmethod
    def register(cls, executor_type: ExecutorType, executor_class: Type[Executor]) -> None:
        """
        注册执行器类型
        
        Args:
            executor_type: 执行器类型
            executor_class: 执行器类
        """
        if not issubclass(executor_class, Executor):
            raise TypeError(f"{executor_class} 必须继承自 Executor")
        cls._executors[executor_type] = executor_class
    
    @classmethod
    def create(cls, executor_type: ExecutorType) -> Executor:
        """
        创建执行器实例
        
        Args:
            executor_type: 执行器类型
            
        Returns:
            执行器实例
            
        Raises:
            ValueError: 不支持的处理类型
        """
        if executor_type not in cls._executors:
            raise ValueError(f"不支持的执行器类型: {executor_type}")
        return cls._executors[executor_type]()
    
    @classmethod
    def create_by_name(cls, name: str) -> Executor:
        """
        通过名称创建执行器
        
        Args:
            name: 执行器名称
            
        Returns:
            执行器实例
        """
        try:
            executor_type = ExecutorType(name)
            return cls.create(executor_type)
        except ValueError:
            raise ValueError(f"未知的执行器名称: {name}")
    
    @classmethod
    def get_supported_types(cls) -> list[ExecutorType]:
        """获取支持的所有执行器类型"""
        return list(cls._executors.keys())
    
    @classmethod
    def unregister(cls, executor_type: ExecutorType) -> None:
        """注销执行器类型"""
        if executor_type in cls._executors:
            del cls._executors[executor_type]
