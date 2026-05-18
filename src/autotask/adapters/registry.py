"""
适配器注册表
"""

from typing import Dict, Type, Optional, List
from dataclasses import dataclass

from autotask.adapters.llm.base import LLMAdapter, LLMConfig


class AdapterRegistry:
    """
    适配器注册表
    
    管理 LLM 适配器的注册和获取
    """
    
    _adapters: Dict[str, Type[LLMAdapter]] = {}
    _instances: Dict[str, LLMAdapter] = {}
    _default_provider: Optional[str] = None
    
    @classmethod
    def register(cls, name: str, adapter_class: Type[LLMAdapter]) -> None:
        """
        注册适配器
        
        Args:
            name: 适配器名称
            adapter_class: 适配器类
        """
        if not issubclass(adapter_class, LLMAdapter):
            raise TypeError(f"{adapter_class} 必须继承自 LLMAdapter")
        cls._adapters[name] = adapter_class
        
        # 设置第一个注册的为默认
        if cls._default_provider is None:
            cls._default_provider = name
    
    @classmethod
    def get(cls, name: str, config: Optional[LLMConfig] = None) -> LLMAdapter:
        """
        获取适配器实例
        
        Args:
            name: 适配器名称
            config: 适配器配置
            
        Returns:
            适配器实例
        """
        # 如果已有实例且无新配置，返回缓存实例
        if name in cls._instances and config is None:
            return cls._instances[name]
        
        if name not in cls._adapters:
            raise ValueError(f"未注册的适配器: {name}")
        
        adapter_class = cls._adapters[name]
        
        if config is None:
            config = LLMConfig(model="default")
        
        instance = adapter_class(config)
        
        # 缓存实例
        cls._instances[name] = instance
        
        return instance
    
    @classmethod
    def create(cls, provider: str, config: LLMConfig) -> LLMAdapter:
        """
        创建适配器（强制创建新实例）
        
        Args:
            provider: 提供商名称
            config: 适配器配置
            
        Returns:
            适配器实例
        """
        if provider not in cls._adapters:
            raise ValueError(f"未注册的适配器: {provider}")
        
        adapter_class = cls._adapters[provider]
        return adapter_class(config)
    
    @classmethod
    def set_default(cls, name: str) -> None:
        """
        设置默认适配器
        
        Args:
            name: 适配器名称
        """
        if name not in cls._adapters:
            raise ValueError(f"未注册的适配器: {name}")
        cls._default_provider = name
    
    @classmethod
    def get_default(cls) -> Optional[str]:
        """获取默认适配器名称"""
        return cls._default_provider
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有注册的适配器"""
        return list(cls._adapters.keys())
    
    @classmethod
    def clear_cache(cls) -> None:
        """清除实例缓存"""
        cls._instances.clear()
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """
        注销适配器
        
        Args:
            name: 适配器名称
        """
        if name in cls._adapters:
            del cls._adapters[name]
        if name in cls._instances:
            del cls._instances[name]
        if cls._default_provider == name:
            cls._default_provider = None


# 预注册内置适配器
def _register_builtin_adapters():
    """注册内置适配器"""
    from autotask.adapters.llm.openai_adapter import OpenAIAdapter
    from autotask.adapters.llm.anthropic_adapter import AnthropicAdapter
    from autotask.adapters.llm.ollama_adapter import OllamaAdapter
    
    AdapterRegistry.register("openai", OpenAIAdapter)
    AdapterRegistry.register("anthropic", AnthropicAdapter)
    AdapterRegistry.register("ollama", OllamaAdapter)
    
    # 设置默认
    AdapterRegistry.set_default("openai")


# 初始化时注册内置适配器
_register_builtin_adapters()


# 全局注册表实例访问函数
_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """获取适配器注册表"""
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry
