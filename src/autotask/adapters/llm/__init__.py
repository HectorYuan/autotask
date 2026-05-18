"""
LLM 适配器模块
"""

from autotask.adapters.llm.base import (
    LLMAdapter,
    LLMResponse,
    LLMMessage,
    MessageRole,
    LLMUsage,
)
from autotask.adapters.registry import AdapterRegistry, get_adapter_registry

__all__ = [
    "LLMAdapter",
    "LLMResponse",
    "LLMMessage",
    "MessageRole",
    "LLMUsage",
    "AdapterRegistry",
    "get_adapter_registry",
]
