"""
事件总线
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    """事件优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class Event:
    """事件对象"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"Event(type={self.type}, id={self.id[:8]}, timestamp={self.timestamp})"


@dataclass
class Subscription:
    """事件订阅"""
    id: str
    event_type: str
    callback: Callable[[Event], None]
    filter_fn: Optional[Callable[[Event], bool]] = None
    priority: EventPriority = EventPriority.NORMAL


class EventBus:
    """
    事件总线
    
    特性：
    - 异步事件发布/订阅
    - 支持事件过滤
    - 支持优先级
    - 支持通配符订阅
    """
    
    def __init__(self, async_mode: bool = True, max_listeners: int = 100):
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._wildcard_subscriptions: List[Subscription] = []
        self._async_mode = async_mode
        self._max_listeners = max_listeners
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._handlers: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return
        self._running = True
        # 启动事件处理任务
        self._handlers.append(asyncio.create_task(self._process_events()))
    
    async def stop(self) -> None:
        """停止事件总线"""
        self._running = False
        for handler in self._handlers:
            handler.cancel()
        self._handlers.clear()
    
    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Event], None],
        filter_fn: Optional[Callable[[Event], bool]] = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> str:
        """
        订阅事件
        
        Args:
            event_type: 事件类型（支持 * 通配符）
            callback: 回调函数
            filter_fn: 过滤函数
            priority: 优先级
            
        Returns:
            订阅 ID
        """
        subscription_id = str(uuid.uuid4())
        
        subscription = Subscription(
            id=subscription_id,
            event_type=event_type,
            callback=callback,
            filter_fn=filter_fn,
            priority=priority,
        )
        
        if "*" in event_type:
            self._wildcard_subscriptions.append(subscription)
        else:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            self._subscriptions[event_type].append(subscription)
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅 ID
            
        Returns:
            是否成功取消
        """
        # 从精确订阅中移除
        for subscriptions in self._subscriptions.values():
            for i, sub in enumerate(subscriptions):
                if sub.id == subscription_id:
                    subscriptions.pop(i)
                    return True
        
        # 从通配符订阅中移除
        for i, sub in enumerate(self._wildcard_subscriptions):
            if sub.id == subscription_id:
                self._wildcard_subscriptions.pop(i)
                return True
        
        return False
    
    async def publish(self, event: Event) -> None:
        """
        发布事件
        
        Args:
            event: 事件对象
        """
        if self._async_mode:
            await self._event_queue.put(event)
        else:
            await self._dispatch_event(event)
    
    async def _process_events(self) -> None:
        """事件处理循环"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._dispatch_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"事件处理错误: {e}")
    
    async def _dispatch_event(self, event: Event) -> None:
        """分发事件"""
        # 获取匹配的订阅
        subscriptions = self._get_matching_subscriptions(event)
        
        # 按优先级排序
        subscriptions.sort(key=lambda s: s.priority.value, reverse=True)
        
        # 调用回调
        for subscription in subscriptions:
            try:
                if subscription.filter_fn is None or subscription.filter_fn(event):
                    result = subscription.callback(event)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                logger.error(f"事件回调执行错误: {e}")
    
    def _get_matching_subscriptions(self, event: Event) -> List[Subscription]:
        """获取匹配的事件订阅"""
        matches = []
        
        # 精确匹配
        if event.type in self._subscriptions:
            matches.extend(self._subscriptions[event.type])
        
        # 通配符匹配
        for sub in self._wildcard_subscriptions:
            if self._match_wildcard(event.type, sub.event_type):
                matches.append(sub)
        
        return matches
    
    def _match_wildcard(self, event_type: str, pattern: str) -> bool:
        """匹配通配符模式"""
        if pattern == "*":
            return True
        
        parts = pattern.split("*")
        if len(parts) == 1:
            return event_type == pattern
        
        # 前缀匹配
        if pattern.startswith("*") and not pattern.endswith("*"):
            return event_type.endswith(parts[-1])
        
        # 后缀匹配
        if pattern.endswith("*") and not pattern.startswith("*"):
            return event_type.startswith(parts[0])
        
        # 中间匹配
        return pattern in event_type
    
    def get_subscription_count(self, event_type: Optional[str] = None) -> int:
        """获取订阅数量"""
        if event_type:
            return len(self._subscriptions.get(event_type, []))
        return sum(len(subs) for subs in self._subscriptions.values()) + len(self._wildcard_subscriptions)
