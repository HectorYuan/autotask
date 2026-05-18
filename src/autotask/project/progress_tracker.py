"""
进度追踪器
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
    CANCELLED = "cancelled"


@dataclass
class Milestone:
    """里程碑"""
    id: str
    project_id: str
    name: str
    description: str = ""
    status: MilestoneStatus = MilestoneStatus.PLANNED
    due_date: Optional[datetime] = None
    achieved_date: Optional[datetime] = None
    completion: float = 0.0  # 0-100
    deliverables: List[str] = field(default_factory=list)  # 交付物列表
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他里程碑
    owner: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProgressSnapshot:
    """进度快照"""
    id: str
    project_id: str
    timestamp: datetime
    overall_progress: float
    task_completed: int
    task_total: int
    milestone_completed: int
    milestone_total: int
    metrics: Dict[str, Any] = field(default_factory=dict)


class ProgressTracker:
    """
    进度追踪器
    
    职责：
    - 追踪项目整体进度
    - 里程碑管理
    - 进度快照
    - 趋势分析
    """
    
    def __init__(self):
        self._milestones: Dict[str, Milestone] = {}
        self._project_milestones: Dict[str, List[str]] = {}
        self._snapshots: List[ProgressSnapshot] = []
        self._project_snapshots: Dict[str, List[str]] = {}
    
    def create_milestone(
        self,
        project_id: str,
        name: str,
        due_date: Optional[datetime] = None,
        **kwargs
    ) -> str:
        """
        创建里程碑
        
        Args:
            project_id: 项目 ID
            name: 里程碑名称
            due_date: 截止日期
            **kwargs: 其他属性
            
        Returns:
            里程碑 ID
        """
        milestone_id = str(uuid.uuid4())
        
        milestone = Milestone(
            id=milestone_id,
            project_id=project_id,
            name=name,
            due_date=due_date,
            **kwargs
        )
        
        self._milestones[milestone_id] = milestone
        
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
        if milestone_id in self._milestones:
            milestone_data["updated_at"] = datetime.now()
            self._milestones[milestone_id].__dict__.update(milestone_data)
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
        if milestone_id in self._milestones:
            milestone = self._milestones[milestone_id]
            milestone.status = MilestoneStatus.ACHIEVED
            milestone.achieved_date = datetime.now()
            milestone.completion = 100.0
            milestone.updated_at = datetime.now()
            return True
        return False
    
    def get_milestones(self, project_id: str) -> List[Milestone]:
        """获取项目里程碑"""
        milestone_ids = self._project_milestones.get(project_id, [])
        return [self._milestones[mid] for mid in milestone_ids if mid in self._milestones]
    
    def get_upcoming_milestones(
        self,
        project_id: str,
        days: int = 7
    ) -> List[Milestone]:
        """
        获取即将到来的里程碑
        
        Args:
            project_id: 项目 ID
            days: 天数范围
            
        Returns:
            即将到来的里程碑列表
        """
        milestones = self.get_milestones(project_id)
        now = datetime.now()
        upcoming = []
        
        for m in milestones:
            if m.status in [MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS]:
                if m.due_date and (m.due_date - now).days <= days:
                    upcoming.append(m)
        
        return sorted(upcoming, key=lambda x: x.due_date or datetime.max)
    
    def get_progress(self, project_id: str) -> float:
        """
        获取项目进度
        
        基于里程碑完成情况计算
        
        Args:
            project_id: 项目 ID
            
        Returns:
            进度百分比 0-100
        """
        milestones = self.get_milestones(project_id)
        if not milestones:
            return 0.0
        
        total = sum(m.completion for m in milestones)
        return total / len(milestones)
    
    def record_snapshot(
        self,
        project_id: str,
        task_completed: int,
        task_total: int,
        milestone_completed: int,
        milestone_total: int,
        **metrics
    ) -> str:
        """
        记录进度快照
        
        Args:
            project_id: 项目 ID
            task_completed: 已完成任务数
            task_total: 任务总数
            milestone_completed: 已完成里程碑数
            milestone_total: 里程碑总数
            
        Returns:
            快照 ID
        """
        snapshot_id = str(uuid.uuid4())
        
        overall_progress = 0.0
        if task_total > 0:
            task_progress = (task_completed / task_total) * 70  # 任务占 70%
        else:
            task_progress = 0.0
        
        if milestone_total > 0:
            milestone_progress = (milestone_completed / milestone_total) * 30  # 里程碑占 30%
        else:
            milestone_progress = 0.0
        
        overall_progress = task_progress + milestone_progress
        
        snapshot = ProgressSnapshot(
            id=snapshot_id,
            project_id=project_id,
            timestamp=datetime.now(),
            overall_progress=overall_progress,
            task_completed=task_completed,
            task_total=task_total,
            milestone_completed=milestone_completed,
            milestone_total=milestone_total,
            metrics=metrics,
        )
        
        self._snapshots.append(snapshot)
        
        if project_id not in self._project_snapshots:
            self._project_snapshots[project_id] = []
        self._project_snapshots[project_id].append(snapshot_id)
        
        return snapshot_id
    
    def get_snapshots(
        self,
        project_id: str,
        limit: Optional[int] = None
    ) -> List[ProgressSnapshot]:
        """
        获取进度快照
        
        Args:
            project_id: 项目 ID
            limit: 返回数量限制
            
        Returns:
            快照列表（按时间倒序）
        """
        snapshot_ids = self._project_snapshots.get(project_id, [])
        snapshots = [self._snapshots[sid] for sid in snapshot_ids]
        snapshots.sort(key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            snapshots = snapshots[:limit]
        
        return snapshots
    
    def get_trend(
        self,
        project_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取进度趋势
        
        Args:
            project_id: 项目 ID
            days: 天数范围
            
        Returns:
            趋势数据列表
        """
        snapshots = self.get_snapshots(project_id)
        now = datetime.now()
        
        # 过滤指定天数内的快照
        trend = []
        for s in snapshots:
            if (now - s.timestamp).days <= days:
                trend.append({
                    "date": s.timestamp.isoformat(),
                    "progress": s.overall_progress,
                    "task_completed": s.task_completed,
                    "task_total": s.task_total,
                    "milestone_completed": s.milestone_completed,
                    "milestone_total": s.milestone_total,
                })
        
        return list(reversed(trend))
    
    def calculate_velocity(self, project_id: str) -> float:
        """
        计算进度速率
        
        每天完成的百分比
        
        Args:
            project_id: 项目 ID
            
        Returns:
            每天完成的进度百分比
        """
        snapshots = self.get_snapshots(project_id, limit=10)
        if len(snapshots) < 2:
            return 0.0
        
        first = snapshots[-1]
        last = snapshots[0]
        
        days_diff = (last.timestamp - first.timestamp).days
        if days_diff == 0:
            return 0.0
        
        progress_diff = last.overall_progress - first.overall_progress
        return progress_diff / days_diff
