"""
AutoTask - 智能任务自动化框架
"""

from autotask.version import __version__
from autotask.core.state_machine import StateMachine
from autotask.core.executor import Executor
from autotask.core.executor_factory import ExecutorFactory, ExecutorType

__all__ = [
    "__version__",
    "StateMachine",
    "Executor",
    "ExecutorFactory",
    "ExecutorType",
]
