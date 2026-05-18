"""
LLM 适配器基类 - 统一接口定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, AsyncIterator
from enum import Enum
import time


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class LLMMessage:
    """LLM 消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMUsage:
    """Token 使用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    finish_reason: str = "stop"
    usage: Optional[LLMUsage] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens if self.usage else 0,
                "completion_tokens": self.usage.completion_tokens if self.usage else 0,
                "total_tokens": self.usage.total_tokens if self.usage else 0,
            } if self.usage else None,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }


@dataclass 
class LLMConfig:
    """LLM 配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    top_k: int = 50
    timeout: int = 60
    retry_count: int = 3
    retry_delay: float = 1.0
    stream: bool = False
    # 额外配置
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMAdapter(ABC):
    """
    LLM 适配器基类
    
    定义统一的 LLM 接口，各 Provider 需实现此接口
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._last_request_time: Optional[float] = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        发送对话请求
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            
        Returns:
            LLM 响应
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式对话请求
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            
        Yields:
            流式响应文本
        """
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        计算 token 数量
        
        Args:
            text: 文本
            
        Returns:
            token 数量
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        验证连接
        
        Returns:
            是否连接成功
        """
        pass
    
    async def prepare_messages(
        self,
        system: Optional[str],
        user: str,
        history: Optional[List[LLMMessage]] = None,
    ) -> List[LLMMessage]:
        """
        准备消息列表
        
        Args:
            system: 系统提示
            user: 用户消息
            history: 历史消息
            
        Returns:
            消息列表
        """
        messages = []
        
        if system:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system))
        
        if history:
            messages.extend(history)
        
        messages.append(LLMMessage(role=MessageRole.USER, content=user))
        
        return messages
    
    def get_rate_limit_delay(self) -> float:
        """
        获取限流延迟
        
        Returns:
            延迟秒数
        """
        if self._last_request_time:
            elapsed = time.time() - self._last_request_time
            if elapsed < 0.1:  # 100ms 间隔
                return 0.1 - elapsed
        return 0.0
    
    def update_request_time(self) -> None:
        """更新最后请求时间"""
        self._last_request_time = time.time()
