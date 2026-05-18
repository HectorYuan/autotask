"""
里程碑追踪器
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MilestoneStatus(str, Enum):
    """里程碑状态"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    DELAYED = "delayed"
    AT_RISK = "at_risk"
    CANCELLED = "cancelled"


@dataclass
class Milestone:
    """
    里程碑
    
    项目或目标的关键节点
    """
    id: str
    goal_id: Optional[str]  # 关联目标
    project_id: Optional[str]  # 关联项目
    name: str  # 里程碑名称
    description: str = ""
    
    # 状态
    status: MilestoneStatus = MilestoneStatus.PLANNED
    
    # 时间
    planned_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    achieved_date: Optional[datetime] = None
    
    # 进度
    completion: float = 0.0  # 0-100
    criteria: List[str] = field(default_factory=list)  # 完成标准
    completed_criteria: List[str] = field(default_factory=list)  # 已完成标准
    
    # 交付物
    deliverables: List[str] = field(default_factory=list)
    
    # 依赖
    dependencies: List[str] = field(default_factory=list)  # 依赖的里程碑 ID
    
    # 归属
    owner: Optional[str] = None
    team: Optional[str] = None
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_overdue(self) -> bool:
        """是否逾期"""
        if self.status in [MilestoneStatus.ACHIEVED, MilestoneStatus.CANCELLED]:
            return False
        if not self.due_date:
            return False
        return datetime.now() > self.due_date
    
    @property
    def days_remaining(self) -> Optional[int]:
        """剩余天数"""
        if not self.due_date:
            return None
        if self.status == MilestoneStatus.ACHIEVED:
            return 0
        delta = self.due_date - datetime.now()
        return max(0, delta.days)


class MilestoneTracker:
    """
    里程碑追踪器
    
    职责：
    - 里程碑创建和管理
    - 进度追踪
    - 依赖管理
    - 预警
    """
    
    def __init__(self):
        self._milestones: Dict[str, Milestone] = {}
        self._goal_milestones: Dict[str, List[str]] = {}  # goal_id -> milestone_ids
        self._project_milestones: Dict[str, List[str]] = {}  # project_id -> milestone_ids
    
    def create_milestone(
        self,
        name: str,
        goal_id: Optional[str] = None,
        project_id: Optional[str] = None,
        due_date: Optional[datetime] = None,
        **kwargs
    ) -> str:
        """
        创建里程碑
        
        Args:
            name: 里程碑名称
            goal_id: 目标 ID（可选）
            project_id: 项目 ID（可选）
            due_date: 截止日期
            **kwargs: 其他属性
            
        Returns:
            里程碑 ID
        """
        milestone_id = str(uuid.uuid4())
        
        milestone = Milestone(
            id=milestone_id,
            goal_id=goal_id,
            project_id=project_id,
            name=name,
            due_date=due_date,
            **kwargs
        )
        
        self._milestones[milestone_id] = milestone
        
        # 关联到目标
        if goal_id:
            if goal_id not in self._goal_milestones:
                self._goal_milestones[goal_id] = []
            self._goal_milestones[goal_id].append(milestone_id)
        
        # 关联到项目
        if project_id:
            if project_id not in self._project_milestones:
                self._project_milestones[project_id] = []
            self._project_milestones[project_id].append(milestone_id)
        
        return milestone_id
    
    def get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """获取里程碑"""
        return self._milestones.get(milestone_id)
    
    def update_milestone(
        self,
        milestone_id: str,
        milestone_data: Dict[str, Any]
    ) -> bool:
        """更新里程碑"""
        if milestone_id not in self._milestones:
            return False
        
        milestone_data["updated_at"] = datetime.now()
        self._milestones[milestone_id].__dict__.update(milestone_data)
        return True
    
    def start_milestone(self, milestone_id: str) -> bool:
        """开始里程碑"""
        if milestone_id in self._milestones:
            self._milestones[milestone_id].status = MilestoneStatus.IN_PROGRESS
            self._milestones[milestone_id].updated_at = datetime.now()
            return True
        return False
    
    def achieve_milestone(self, milestone_id: str) -> bool:
        """
        达成里程碑
        
        Args:
            milestone_id: 里程碑 ID
            
        Returns:
            是否成功
        """
        if milestone_id not in self._milestones:
            return False
        
        milestone = self._milestones[milestone_id]
        milestone.status = MilestoneStatus.ACHIEVED
        milestone.achieved_date = datetime.now()
        milestone.completion = 100.0
        milestone.completed_criteria = list(milestone.criteria)
        milestone.updated_at = datetime.now()
        
        return True
    
    def delay_milestone(self, milestone_id: str, new_due_date: datetime) -> bool:
        """
        延迟里程碑
        
        Args:
            milestone_id: 里程碑 ID
            new_due_date: 新的截止日期
            
        Returns:
            是否成功
        """
        if milestone_id in self._milestones:
            self._milestones[milestone_id].due_date = new_due_date
            self._milestones[milestone_id].status = MilestoneStatus.DELAYED
            self._milestones[milestone_id].updated_at = datetime.now()
            return True
        return False
    
    def update_completion(
        self,
        milestone_id: str,
        completion: float
    ) -> bool:
        """
        更新完成度
        
        Args:
            milestone_id: 里程碑 ID
            completion: 完成度 (0-100)
            
        Returns:
            是否成功
        """
        if milestone_id not in self._milestones:
            return False
        
        milestone = self._milestones[milestone_id]
        milestone.completion = min(100, max(0, completion))
        milestone.updated_at = datetime.now()
        
        # 如果完成度达到 100%，自动标记为达成
        if milestone.completion >= 100 and milestone.status == MilestoneStatus.IN_PROGRESS:
            self.achieve_milestone(milestone_id)
        
        return True
    
    def add_criteria(self, milestone_id: str, criteria: str) -> bool:
        """添加完成标准"""
        if milestone_id in self._milestones:
            if criteria not in self._milestones[milestone_id].criteria:
                self._milestones[milestone_id].criteria.append(criteria)
            self._milestones[milestone_id].updated_at = datetime.now()
            return True
        return False
    
    def complete_criteria(self, milestone_id: str, criteria: str) -> bool:
        """标记标准完成"""
        if milestone_id in self._milestones:
            milestone = self._milestones[milestone_id]
            if criteria in milestone.criteria and criteria not in milestone.completed_criteria:
                milestone.completed_criteria.append(criteria)
                milestone.completion = (len(milestone.completed_criteria) / len(milestone.criteria)) * 100
                milestone.updated_at = datetime.now()
                
                # 如果所有标准都完成，自动达成里程碑
                if len(milestone.completed_criteria) >= len(milestone.criteria):
                    self.achieve_milestone(milestone_id)
                return True
        return False
    
    def add_dependency(self, milestone_id: str, depends_on_id: str) -> bool:
        """
        添加依赖
        
        Args:
            milestone_id: 当前里程碑 ID
            depends_on_id: 依赖的里程碑 ID
            
        Returns:
            是否成功
        """
        if milestone_id not in self._milestones or depends_on_id not in self._milestones:
            return False
        
        if depends_on_id not in self._milestones[milestone_id].dependencies:
            self._milestones[milestone_id].dependencies.append(depends_on_id)
            self._milestones[milestone_id].updated_at = datetime.now()
        return True
    
    def can_start(self, milestone_id: str) -> bool:
        """
        检查里程碑是否可以开始
        
        所有依赖都已达成
        
        Args:
            milestone_id: 里程碑 ID
            
        Returns:
            是否可以开始
        """
        milestone = self._milestones.get(milestone_id)
        if not milestone:
            return False
        
        for dep_id in milestone.dependencies:
            dep = self._milestones.get(dep_id)
            if not dep or dep.status != MilestoneStatus.ACHIEVED:
                return False
        
        return True
    
    def get_milestones_by_goal(self, goal_id: str) -> List[Milestone]:
        """获取目标里程碑"""
        milestone_ids = self._goal_milestones.get(goal_id, [])
        return [self._milestones[mid] for mid in milestone_ids if mid in self._milestones]
    
    def get_milestones_by_project(self, project_id: str) -> List[Milestone]:
        """获取项目里程碑"""
        milestone_ids = self._project_milestones.get(project_id, [])
        return [self._milestones[mid] for mid in milestone_ids if mid in self._milestones]
    
    def get_upcoming(self, days: int = 7) -> List[Milestone]:
        """
        获取即将到来的里程碑
        
        Args:
            days: 天数范围
            
        Returns:
            里程碑列表
        """
        now = datetime.now()
        upcoming = []
        
        for milestone in self._milestones.values():
            if milestone.status in [MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS]:
                if milestone.due_date:
                    delta = (milestone.due_date - now).days
                    if 0 <= delta <= days:
                        upcoming.append(milestone)
        
        return sorted(upcoming, key=lambda m: m.due_date or datetime.max)
    
    def get_overdue(self) -> List[Milestone]:
        """获取逾期里程碑"""
        return [m for m in self._milestones.values() if m.is_overdue]
    
    def get_at_risk(self) -> List[Milestone]:
        """
        获取风险里程碑
        
        风险：进度落后于计划
        """
        at_risk = []
        
        for milestone in self._milestones.values():
            if milestone.status not in [MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS]:
                continue
            
            if not milestone.planned_date or not milestone.due_date:
                continue
            
            # 计算计划进度
            total_days = (milestone.due_date - milestone.planned_date).days
            if total_days <= 0:
                continue
            
            elapsed_days = (datetime.now() - milestone.planned_date).days
            expected_progress = (elapsed_days / total_days) * 100
            
            # 如果实际进度落后于计划 20% 以上，标记为风险
            if milestone.completion < expected_progress * 0.8:
                at_risk.append(milestone)
        
        return at_risk
    
    def check_and_update_status(self, milestone_id: str) -> None:
        """
        检查并更新里程碑状态
        
        根据进度和时间自动更新状态
        """
        milestone = self._milestones.get(milestone_id)
        if not milestone:
            return
        
        # 检查逾期
        if milestone.is_overdue and milestone.status == MilestoneStatus.IN_PROGRESS:
            milestone.status = MilestoneStatus.AT_RISK
            milestone.updated_at = datetime.now()
        
        # 检查风险
        at_risk_list = self.get_at_risk()
        if milestone in at_risk_list:
            milestone.status = MilestoneStatus.AT_RISK
            milestone.updated_at = datetime.now()
