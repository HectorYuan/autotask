"""
Ollama 适配器
P1 - 优先级次之，支持本地部署
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


class OllamaAdapter(LLMAdapter):
    """
    Ollama API 适配器
    
    支持本地部署的 LLM
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.extra.get("base_url", "http://localhost:11434")
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    @property
    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={"Content-Type": "application/json"},
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
        ollama_messages = self._convert_messages(messages)
        
        # 构建请求
        request_data: Dict[str, Any] = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": False,
        }
        
        # Ollama 参数
        if self.config.temperature != 0.7:
            request_data["options"] = {"temperature": self.config.temperature}
        
        if self.config.max_tokens != 4096:
            if "options" not in request_data:
                request_data["options"] = {}
            request_data["options"]["num_predict"] = self.config.max_tokens
        
        # 发送请求
        url = f"{self.base_url}/api/chat"
        response = await self._http_client.post(url, json=request_data)
        
        self.update_request_time()
        
        if response.status_code != 200:
            raise Exception(f"Ollama API 错误: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # 解析响应
        message = data.get("message", {})
        
        # 提取 usage (Ollama 可能不返回)
        usage = None
        if "_eval_count" in data:
            usage = LLMUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )
        
        return LLMResponse(
            content=message.get("content", ""),
            model=self.config.model,
            finish_reason=data.get("done_reason", "stop"),
            usage=usage,
            metadata={"done": data.get("done", True)},
        )
    
    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话请求"""
        # 转换消息格式
        ollama_messages = self._convert_messages(messages)
        
        # 构建请求
        request_data = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": True,
        }
        
        # 发送请求
        url = f"{self.base_url}/api/chat"
        async with self._http_client.stream("POST", url, json=request_data) as response:
            self.update_request_time()
            
            async for line in response.aiter_lines():
                if line:
                    import json
                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def count_tokens(self, text: str) -> int:
        """
        计算 token 数量
        
        Ollama 没有内置 token 计算，使用简单估算
        """
        # 简单估算
        chinese_chars = sum(1 for c in text if ord(c) > 127)
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    async def validate_connection(self) -> bool:
        """验证连接"""
        try:
            url = f"{self.base_url}/api/tags"
            response = await self._http_client.get(url)
            return response.status_code == 200
        except Exception:
            return False
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """转换消息格式"""
        result = []
        for msg in messages:
            result.append({
                "role": msg.role.value,
                "content": msg.content,
            })
        return result
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        列出可用模型
        
        Returns:
            模型列表
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = await self._http_client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
        except Exception:
            pass
        return []
    
    async def pull_model(self, model: str) -> AsyncIterator[str]:
        """
        拉取模型
        
        Args:
            model: 模型名称
            
        Yields:
            进度信息
        """
        url = f"{self.base_url}/api/pull"
        async with self._http_client.stream("POST", url, json={"name": model}) as response:
            async for line in response.aiter_lines():
                if line:
                    import json
                    try:
                        data = json.loads(line)
                        if "status" in data:
                            yield data["status"]
                    except json.JSONDecodeError:
                        continue
    
    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
