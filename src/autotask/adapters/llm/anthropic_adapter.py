"""
Anthropic 适配器
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


class AnthropicAdapter(LLMAdapter):
    """
    Anthropic API 适配器
    
    支持 Claude 3 系列模型
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or config.extra.get("api_key")
        self.base_url = config.extra.get("base_url", "https://api.anthropic.com/v1")
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
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
        
        # Anthropic 使用 system 和 messages
        anthropic_messages = []
        system_prompt = ""
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                anthropic_messages.append({
                    "role": self._convert_role(msg.role),
                    "content": msg.content,
                })
        
        # 构建请求
        request_data: Dict[str, Any] = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        if system_prompt:
            request_data["system"] = system_prompt
        
        if tools:
            request_data["tools"] = [self._convert_tool(tool) for tool in tools]
        
        # 发送请求
        url = f"{self.base_url}/messages"
        response = await self._http_client.post(url, json=request_data)
        
        self.update_request_time()
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API 错误: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # 解析响应
        content = data["content"][0] if data.get("content") else {"text": ""}
        
        # 提取 usage
        usage = None
        if "usage" in data:
            usage = LLMUsage(
                input_tokens=data["usage"].get("input_tokens", 0),
                output_tokens=data["usage"].get("output_tokens", 0),
                total_tokens=data["usage"].get("input_tokens", 0) + data["usage"].get("output_tokens", 0),
            )
        
        # 处理停止原因
        stop_reason = data.get("stop_reason", "end_turn")
        finish_reason = "stop" if stop_reason == "end_turn" else stop_reason
        
        return LLMResponse(
            content=content.get("text", ""),
            model=data["model"],
            finish_reason=finish_reason,
            usage=usage,
            metadata=data.get("metadata", {}),
        )
    
    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话请求（Anthropic 使用不同格式）"""
        # 转换消息
        anthropic_messages = []
        system_prompt = ""
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                anthropic_messages.append({
                    "role": self._convert_role(msg.role),
                    "content": msg.content,
                })
        
        # 构建请求
        request_data: Dict[str, Any] = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        
        if system_prompt:
            request_data["system"] = system_prompt
        
        if tools:
            request_data["tools"] = [self._convert_tool(tool) for tool in tools]
        
        # 发送请求
        url = f"{self.base_url}/messages"
        async with self._http_client.stream("POST", url, json=request_data) as response:
            self.update_request_time()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    import json
                    data = json.loads(data_str)
                    
                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
    
    async def count_tokens(self, text: str) -> int:
        """
        计算 token 数量
        
        Claude 使用 Claude Tokenizer，简化估算
        """
        # 简单估算
        chinese_chars = sum(1 for c in text if ord(c) > 127)
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    async def validate_connection(self) -> bool:
        """验证连接"""
        try:
            # Anthropic 没有 list models 接口，使用简单请求验证
            url = f"{self.base_url}/messages"
            response = await self._http_client.post(
                url,
                json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                }
            )
            return response.status_code in [200, 400]  # 400 也表示认证通过
        except Exception:
            return False
    
    def _convert_role(self, role: MessageRole) -> str:
        """转换角色"""
        mapping = {
            MessageRole.USER: "user",
            MessageRole.ASSISTANT: "assistant",
        }
        return mapping.get(role, "user")
    
    def _convert_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """转换工具定义"""
        # Anthropic 工具格式与 OpenAI 不同
        return {
            "name": tool["function"]["name"],
            "description": tool["function"].get("description", ""),
            "input_schema": tool["function"]["parameters"],
        }
    
    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
