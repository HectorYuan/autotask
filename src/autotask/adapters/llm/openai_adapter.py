"""
OpenAI 适配器
P0 - 优先级最高
"""

import os
from typing import List, Optional, Dict, Any, AsyncIterator
import httpx

from autotask.adapters.llm.base import (
    LLMAdapter,
    LLMResponse,
    LLMMessage,
    LLMConfig,
    LLMUsage,
    MessageRole,
)


class OpenAIAdapter(LLMAdapter):
    """
    OpenAI API 适配器
    
    支持 GPT-4、GPT-3.5 等模型
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = os.getenv("OPENAI_API_KEY") or config.extra.get("api_key")
        self.base_url = config.extra.get("base_url", "https://api.openai.com/v1")
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client
    
    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """发送对话请求"""
        # 限流
        delay = self.get_rate_limit_delay()
        if delay > 0:
            import asyncio
            await asyncio.sleep(delay)
        
        # 转换消息格式
        openai_messages = self._convert_messages(messages)
        
        # 构建请求
        request_data = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
        }
        
        if tools:
            request_data["tools"] = tools
            request_data["tool_choice"] = "auto"
        
        # 发送请求
        url = f"{self.base_url}/chat/completions"
        response = await self._http_client.post(url, json=request_data)
        
        self.update_request_time()
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API 错误: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # 解析响应
        choice = data["choices"][0]
        message = choice["message"]
        
        # 提取 usage
        usage = None
        if "usage" in data:
            usage = LLMUsage(
                prompt_tokens=data["usage"].get("prompt_tokens", 0),
                completion_tokens=data["usage"].get("completion_tokens", 0),
                total_tokens=data["usage"].get("total_tokens", 0),
            )
        
        return LLMResponse(
            content=message.get("content", ""),
            model=data["model"],
            finish_reason=choice.get("finish_reason", "stop"),
            usage=usage,
            tool_calls=message.get("tool_calls"),
            metadata=data.get("metadata", {}),
        )
    
    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话请求"""
        # 转换消息格式
        openai_messages = self._convert_messages(messages)
        
        # 构建请求
        request_data = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "stream": True,
        }
        
        if tools:
            request_data["tools"] = tools
        
        # 发送请求
        url = f"{self.base_url}/chat/completions"
        async with self._http_client.stream("POST", url, json=request_data) as response:
            self.update_request_time()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    import json
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
    
    async def count_tokens(self, text: str) -> int:
        """
        计算 token 数量
        
        使用简单的估算：中文约 2 tokens/字符，英文约 0.25 tokens/字符
        """
        # 简单估算
        chinese_chars = sum(1 for c in text if ord(c) > 127)
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    async def validate_connection(self) -> bool:
        """验证连接"""
        try:
            url = f"{self.base_url}/models"
            response = await self._http_client.get(url)
            return response.status_code == 200
        except Exception:
            return False
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """转换消息格式"""
        result = []
        for msg in messages:
            item = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                item["name"] = msg.name
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            result.append(item)
        return result
    
    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
