"""
目标管理器
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class GoalStatus(str, Enum):
    """目标状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    ACHIEVED = "achieved"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class GoalPriority(str, Enum):
    """目标优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Goal:
    """
    目标定义
    
    符合 OKR 风格的目标定义
    """
    id: str
    project_id: Optional[str]  # 可关联项目
    title: str  # 目标标题
    description: str = ""  # 目标描述
    status: GoalStatus = GoalStatus.DRAFT
    priority: GoalPriority = GoalPriority.MEDIUM
    
    # 关键结果
    key_results: List[str] = field(default_factory=list)
    
    # 进度跟踪
    progress: float = 0.0  # 0-100
    current_value: float = 0.0
    target_value: float = 100.0
    
    # 时间范围
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    achieved_date: Optional[datetime] = None
    
    # 归属
    owner: Optional[str] = None
    team: Optional[str] = None
    
    # 关联
    parent_goal_id: Optional[str] = None  # 父目标
    child_goal_ids: List[str] = field(default_factory=list)  # 子目标
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_aligned(self) -> bool:
        """是否已对齐（有关联项目或父目标）"""
        return self.project_id is not None or self.parent_goal_id is not None
    
    @property
    def is_on_track(self) -> bool:
        """是否在正常轨道上"""
        if self.status != GoalStatus.ACTIVE:
            return True
        
        if not self.due_date:
            return True
        
        now = datetime.now()
        time_elapsed = (now - (self.start_date or now)).days
        total_time = (self.due_date - (self.start_date or now)).days
        
        if total_time <= 0:
            return True
        
        expected_progress = (time_elapsed / total_time) * 100
        return self.progress >= expected_progress * 0.8  # 允许 20% 的容差


class GoalManager:
    """
    目标管理器
    
    职责：
    - 目标的创建和管理
    - OKR 风格的层级结构
    - 目标对齐
    - 进度跟踪
    """
    
    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._project_goals: Dict[str, List[str]] = {}  # project_id -> goal_ids
        self._owner_goals: Dict[str, List[str]] = {}  # owner -> goal_ids
    
    def create_goal(
        self,
        title: str,
        project_id: Optional[str] = None,
        description: str = "",
        **kwargs
    ) -> str:
        """
        创建目标
        
        Args:
            title: 目标标题
            project_id: 项目 ID（可选）
            description: 目标描述
            **kwargs: 其他属性
            
        Returns:
            目标 ID
        """
        goal_id = str(uuid.uuid4())
        
        goal = Goal(
            id=goal_id,
            project_id=project_id,
            title=title,
            description=description,
            **kwargs
        )
        
        self._goals[goal_id] = goal
        
        # 关联到项目
        if project_id:
            if project_id not in self._project_goals:
                self._project_goals[project_id] = []
            self._project_goals[project_id].append(goal_id)
        
        # 关联到负责人
        if goal.owner:
            if goal.owner not in self._owner_goals:
                self._owner_goals[goal.owner] = []
            self._owner_goals[goal.owner].append(goal_id)
        
        return goal_id
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """获取目标"""
        return self._goals.get(goal_id)
    
    def update_goal(self, goal_id: str, goal_data: Dict[str, Any]) -> bool:
        """
        更新目标
        
        Args:
            goal_id: 目标 ID
            goal_data: 更新数据
            
        Returns:
            是否成功
        """
        if goal_id not in self._goals:
            return False
        
        old_goal = self._goals[goal_id]
        goal_data["updated_at"] = datetime.now()
        old_goal.__dict__.update(goal_data)
        
        # 处理负责人变更
        if "owner" in goal_data and goal_data["owner"] != old_goal.owner:
            # 从旧负责人列表移除
            if old_goal.owner and old_goal.owner in self._owner_goals:
                if goal_id in self._owner_goals[old_goal.owner]:
                    self._owner_goals[old_goal.owner].remove(goal_id)
            
            # 添加到新负责人列表
            new_owner = goal_data["owner"]
            if new_owner:
                if new_owner not in self._owner_goals:
                    self._owner_goals[new_owner] = []
                self._owner_goals[new_owner].append(goal_id)
        
        return True
    
    def delete_goal(self, goal_id: str) -> bool:
        """删除目标"""
        if goal_id not in self._goals:
            return False
        
        goal = self._goals[goal_id]
        
        # 从项目列表移除
        if goal.project_id and goal.project_id in self._project_goals:
            if goal_id in self._project_goals[goal.project_id]:
                self._project_goals[goal.project_id].remove(goal_id)
        
        # 从负责人列表移除
        if goal.owner and goal.owner in self._owner_goals:
            if goal_id in self._owner_goals[goal.owner]:
                self._owner_goals[goal.owner].remove(goal_id)
        
        # 更新父目标
        if goal.parent_goal_id and goal.parent_goal_id in self._goals:
            parent = self._goals[goal.parent_goal_id]
            if goal_id in parent.child_goal_ids:
                parent.child_goal_ids.remove(goal_id)
        
        del self._goals[goal_id]
        return True
    
    def activate_goal(self, goal_id: str) -> bool:
        """激活目标"""
        if goal_id in self._goals:
            self._goals[goal_id].status = GoalStatus.ACTIVE
            self._goals[goal_id].start_date = datetime.now()
            self._goals[goal_id].updated_at = datetime.now()
            return True
        return False
    
    def achieve_goal(self, goal_id: str) -> bool:
        """完成目标"""
        if goal_id in self._goals:
            goal = self._goals[goal_id]
            goal.status = GoalStatus.ACHIEVED
            goal.achieved_date = datetime.now()
            goal.progress = 100.0
            goal.updated_at = datetime.now()
            
            # 更新父目标进度
            self._update_parent_progress(goal_id)
            
            return True
        return False
    
    def _update_parent_progress(self, child_goal_id: str) -> None:
        """更新父目标进度"""
        goal = self._goals.get(child_goal_id)
        if not goal or not goal.parent_goal_id:
            return
        
        parent = self._goals.get(goal.parent_goal_id)
        if not parent:
            return
        
        # 计算所有子目标的平均进度
        total_progress = sum(
            self._goals[gid].progress
            for gid in parent.child_goal_ids
            if gid in self._goals
        )
        
        parent.progress = total_progress / len(parent.child_goal_ids) if parent.child_goal_ids else 0
        parent.updated_at = datetime.now()
    
    def update_progress(
        self,
        goal_id: str,
        current_value: float,
        progress: Optional[float] = None
    ) -> bool:
        """
        更新目标进度
        
        Args:
            goal_id: 目标 ID
            current_value: 当前值
            progress: 进度百分比（可选，不提供则自动计算）
            
        Returns:
            是否成功
        """
        if goal_id not in self._goals:
            return False
        
        goal = self._goals[goal_id]
        goal.current_value = current_value
        
        if progress is not None:
            goal.progress = progress
        elif goal.target_value > 0:
            goal.progress = min(100, (current_value / goal.target_value) * 100)
        
        goal.updated_at = datetime.now()
        
        # 如果达到目标，自动标记为完成
        if goal.progress >= 100 and goal.status == GoalStatus.ACTIVE:
            self.achieve_goal(goal_id)
        
        return True
    
    def add_key_result(self, goal_id: str, key_result: str) -> bool:
        """添加关键结果"""
        if goal_id in self._goals:
            if key_result not in self._goals[goal_id].key_results:
                self._goals[goal_id].key_results.append(key_result)
            self._goals[goal_id].updated_at = datetime.now()
            return True
        return False
    
    def align_goals(self, child_goal_id: str, parent_goal_id: str) -> bool:
        """
        对齐目标（父子关系）
        
        Args:
            child_goal_id: 子目标 ID
            parent_goal_id: 父目标 ID
            
        Returns:
            是否成功
        """
        if child_goal_id not in self._goals or parent_goal_id not in self._goals:
            return False
        
        child = self._goals[child_goal_id]
        parent = self._goals[parent_goal_id]
        
        # 移除旧的父子关系
        if child.parent_goal_id and child.parent_goal_id in self._goals:
            old_parent = self._goals[child.parent_goal_id]
            if child_goal_id in old_parent.child_goal_ids:
                old_parent.child_goal_ids.remove(child_goal_id)
        
        # 建立新的父子关系
        child.parent_goal_id = parent_goal_id
        parent.child_goal_ids.append(child_goal_id)
        
        child.updated_at = datetime.now()
        parent.updated_at = datetime.now()
        
        return True
    
    def get_goals_by_project(self, project_id: str) -> List[Goal]:
        """获取项目目标"""
        goal_ids = self._project_goals.get(project_id, [])
        return [self._goals[gid] for gid in goal_ids if gid in self._goals]
    
    def get_goals_by_owner(self, owner: str) -> List[Goal]:
        """获取负责人目标"""
        goal_ids = self._owner_goals.get(owner, [])
        return [self._goals[gid] for gid in goal_ids if gid in self._goals]
    
    def get_active_goals(self, project_id: Optional[str] = None) -> List[Goal]:
        """
        获取活跃目标
        
        Args:
            project_id: 项目 ID（可选）
            
        Returns:
            活跃目标列表
        """
        if project_id:
            goals = self.get_goals_by_project(project_id)
        else:
            goals = list(self._goals.values())
        
        return [g for g in goals if g.status == GoalStatus.ACTIVE]
    
    def get_off_track_goals(self) -> List[Goal]:
        """获取偏离轨道目标"""
        active = self.get_active_goals()
        return [g for g in active if not g.is_on_track]
    
    def get_child_goals(self, goal_id: str) -> List[Goal]:
        """获取子目标"""
        goal = self._goals.get(goal_id)
        if not goal:
            return []
        return [self._goals[gid] for gid in goal.child_goal_ids if gid in self._goals]
    
    def get_parent_goal(self, goal_id: str) -> Optional[Goal]:
        """获取父目标"""
        goal = self._goals.get(goal_id)
        if not goal or not goal.parent_goal_id:
            return None
        return self._goals.get(goal.parent_goal_id)
