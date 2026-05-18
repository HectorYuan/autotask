"""
配置管理模块
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60


@dataclass
class StorageConfig:
    """存储配置"""
    backend: str = "memory"  # memory, sqlite, postgres
    connection_string: Optional[str] = None
    base_path: Path = field(default_factory=lambda: Path("./data"))


@dataclass
class EventBusConfig:
    """事件总线配置"""
    async_mode: bool = True
    max_listeners: int = 100
    buffer_size: int = 1000


@dataclass
class ExecutorConfig:
    """执行器配置"""
    max_concurrent: int = 5
    timeout: int = 300
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class AutoTaskConfig:
    """AutoTask 主配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    log_level: str = "INFO"
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AutoTaskConfig":
        """从环境变量加载配置"""
        return cls(
            llm=LLMConfig(
                provider=os.getenv("AUTOTASK_LLM_PROVIDER", "openai"),
                model=os.getenv("AUTOTASK_LLM_MODEL", "gpt-4"),
                api_key=os.getenv("AUTOTASK_LLM_API_KEY"),
                base_url=os.getenv("AUTOTASK_LLM_BASE_URL"),
            ),
            storage=StorageConfig(
                backend=os.getenv("AUTOTASK_STORAGE_BACKEND", "memory"),
                connection_string=os.getenv("AUTOTASK_STORAGE_CONN"),
                base_path=Path(os.getenv("AUTOTASK_STORAGE_PATH", "./data")),
            ),
            log_level=os.getenv("AUTOTASK_LOG_LEVEL", "INFO"),
            debug=os.getenv("AUTOTASK_DEBUG", "false").lower() == "true",
        )


# 全局配置实例
_config: Optional[AutoTaskConfig] = None


def get_config() -> AutoTaskConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = AutoTaskConfig.from_env()
    return _config


def set_config(config: AutoTaskConfig) -> None:
    """设置全局配置"""
    global _config
    _config = config
