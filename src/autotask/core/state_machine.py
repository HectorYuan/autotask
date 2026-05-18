"""
通用状态机 - 替代 TaskMachine
单一职责：状态转换逻辑
"""

from typing import Dict, Set, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    """状态基类"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Transition:
    """状态转换定义"""
    from_state: str
    event: str
    to_state: str
    condition: Optional[Callable[[], bool]] = None
    before_callback: Optional[Callable[[], None]] = None
    after_callback: Optional[Callable[[], None]] = None


class StateMachine:
    """
    通用状态机
    
    特性：
    - 单一职责：只负责状态转换
    - 支持条件转换
    - 支持转换前后回调
    - 支持状态监听器
    """
    
    def __init__(
        self,
        states: Set[str],
        transitions: List[Transition],
        initial_state: str,
        final_states: Optional[Set[str]] = None
    ):
        """
        初始化状态机
        
        Args:
            states: 所有可能状态集合
            transitions: 转换规则列表
            initial_state: 初始状态
            final_states: 终态集合，默认为 COMPLETED | FAILED | CANCELLED
        """
        self._states = states
        self._transitions = self._build_transition_map(transitions)
        self._current_state = initial_state
        self._final_states = final_states or {State.COMPLETED, State.FAILED, State.CANCELLED}
        self._listeners: Dict[str, List[Callable[[str, str], None]]] = {}
        
        # 验证初始状态有效性
        if initial_state not in states:
            raise ValueError(f"初始状态 '{initial_state}' 不在已知状态集合中")
    
    def _build_transition_map(
        self, 
        transitions: List[Transition]
    ) -> Dict[tuple, Transition]:
        """构建状态转换映射"""
        transition_map = {}
        for t in transitions:
            key = (t.from_state, t.event)
            if key in transition_map:
                raise ValueError(f"重复的转换规则: {t.from_state} + {t.event}")
            transition_map[key] = t
        return transition_map
    
    def transition(self, event: str) -> bool:
        """
        执行状态转换
        
        Args:
            event: 触发事件
            
        Returns:
            转换是否成功
        """
        key = (self._current_state, event)
        if key not in self._transitions:
            return False
        
        transition = self._transitions[key]
        
        # 检查条件
        if transition.condition and not transition.condition():
            return False
        
        old_state = self._current_state
        
        # 执行前置回调
        if transition.before_callback:
            transition.before_callback()
        
        # 执行转换
        self._current_state = transition.to_state
        
        # 执行后置回调
        if transition.after_callback:
            transition.after_callback()
        
        # 通知监听器
        self._notify_listeners(old_state, self._current_state)
        
        return True
    
    def can_transition(self, event: str) -> bool:
        """
        检查是否可以从当前状态转换
        
        Args:
            event: 触发事件
            
        Returns:
            是否可转换
        """
        key = (self._current_state, event)
        if key not in self._transitions:
            return False
        
        transition = self._transitions[key]
        if transition.condition:
            return transition.condition()
        return True
    
    def get_available_events(self) -> List[str]:
        """
        获取当前状态可用的所有事件
        
        Returns:
            可用事件列表
        """
        available = []
        for (state, event), transition in self._transitions.items():
            if state == self._current_state:
                if transition.condition is None or transition.condition():
                    available.append(event)
        return available
    
    @property
    def current_state(self) -> str:
        """获取当前状态"""
        return self._current_state
    
    @property
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self._current_state in self._final_states
    
    def add_listener(self, state: str, callback: Callable[[str, str], None]) -> None:
        """
        添加状态监听器
        
        Args:
            state: 监听的状态（空字符串表示监听所有）
            callback: 回调函数 (from_state, to_state) -> None
        """
        if state not in self._listeners:
            self._listeners[state] = []
        self._listeners[state].append(callback)
    
    def _notify_listeners(self, from_state: str, to_state: str) -> None:
        """通知监听器"""
        for state, callbacks in self._listeners.items():
            if state == "" or state == to_state:
                for callback in callbacks:
                    callback(from_state, to_state)
    
    def reset(self, initial_state: Optional[str] = None) -> None:
        """
        重置状态机
        
        Args:
            initial_state: 重置到的状态，默认为初始状态
        """
        self._current_state = initial_state or list(self._states)[0]
    
    def __repr__(self) -> str:
        return f"StateMachine(current={self._current_state}, states={self._states})"


class TaskStateMachine(StateMachine):
    """
    任务专用状态机
    
    预定义任务状态流转:
    PENDING -> RUNNING -> COMPLETED/FAILED/CANCELLED
    """
    
    TASK_STATES = {
        State.PENDING,
        State.RUNNING,
        State.COMPLETED,
        State.FAILED,
        State.CANCELLED,
    }
    
    TASK_TRANSITIONS = [
        Transition(State.PENDING, "start", State.RUNNING),
        Transition(State.RUNNING, "complete", State.COMPLETED),
        Transition(State.RUNNING, "fail", State.FAILED),
        Transition(State.RUNNING, "cancel", State.CANCELLED),
        Transition(State.PENDING, "cancel", State.CANCELLED),
    ]
    
    def __init__(self, initial_state: str = State.PENDING):
        super().__init__(
            states=self.TASK_STATES,
            transitions=self.TASK_TRANSITIONS,
            initial_state=initial_state,
        )
    
    def start(self) -> bool:
        """开始任务"""
        return self.transition("start")
    
    def complete(self) -> bool:
        """完成任务"""
        return self.transition("complete")
    
    def fail(self) -> bool:
        """标记失败"""
        return self.transition("fail")
    
    def cancel(self) -> bool:
        """取消任务"""
        return self.transition("cancel")
