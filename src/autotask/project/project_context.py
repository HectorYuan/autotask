"""
项目上下文聚合视图
组合查询，不承担业务逻辑
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from autotask.project.wbs_engine import WBSEngine, WBSTask
from autotask.project.risk_manager import RiskManager, Risk
from autotask.project.quality_manager import QualityManager, QualityMetrics
from autotask.project.progress_tracker import ProgressTracker


@dataclass
class ProjectOverview:
    """
    项目全景视图
    
    聚合项目所有关键信息
    """
    project_id: str
    project_name: str
    description: str
    status: str
    progress: float  # 0-100
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # WBS 信息
    total_tasks: int = 0
    completed_tasks: int = 0
    wbs_tree: Optional[Dict[str, Any]] = None
    
    # 风险管理
    risk_count: int = 0
    high_risk_count: int = 0
    risks: List[Dict[str, Any]] = field(default_factory=list)
    
    # 质量管理
    quality_metrics: Optional[QualityMetrics] = None
    
    # 资源使用
    budget_allocated: float = 0.0
    budget_used: float = 0.0
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProjectManager:
    """
    项目管理器
    
    职责：
    - 项目的增删改查
    - 不涉及具体业务逻辑
    """
    
    def __init__(self):
        self._projects: Dict[str, Dict[str, Any]] = {}
    
    def create(self, project_data: Dict[str, Any]) -> str:
        """创建项目"""
        project_id = project_data.get("id") or self._generate_id()
        project_data["id"] = project_id
        project_data["created_at"] = datetime.now()
        self._projects[project_id] = project_data
        return project_id
    
    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目"""
        return self._projects.get(project_id)
    
    def update(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """更新项目"""
        if project_id in self._projects:
            project_data["updated_at"] = datetime.now()
            self._projects[project_id].update(project_data)
            return True
        return False
    
    def delete(self, project_id: str) -> bool:
        """删除项目"""
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False
    
    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出项目"""
        projects = list(self._projects.values())
        if status:
            projects = [p for p in projects if p.get("status") == status]
        return projects
    
    def _generate_id(self) -> str:
        """生成项目 ID"""
        import uuid
        return str(uuid.uuid4())


class ProjectContext:
    """
    项目上下文聚合视图
    
    职责：
    - 组合查询多个 Manager 的数据
    - 提供聚合视图
    - 不承担业务逻辑
    """
    
    def __init__(
        self,
        project_mgr: Optional[ProjectManager] = None,
        wbs_engine: Optional[WBSEngine] = None,
        risk_mgr: Optional[RiskManager] = None,
        quality_mgr: Optional[QualityManager] = None,
        progress_tracker: Optional[ProgressTracker] = None,
    ):
        self._project = project_mgr or ProjectManager()
        self._wbs = wbs_engine or WBSEngine()
        self._risk = risk_mgr or RiskManager()
        self._quality = quality_mgr or QualityManager()
        self._progress = progress_tracker or ProgressTracker()
    
    def get_project_overview(self, project_id: str) -> Optional[ProjectOverview]:
        """
        获取项目全景视图
        
        组合查询，不重复业务逻辑
        
        Args:
            project_id: 项目 ID
            
        Returns:
            项目全景视图
        """
        # 组合查询各 Manager
        project = self._project.get(project_id)
        if not project:
            return None
        
        # WBS 树
        wbs_tree = self._wbs.get_tree(project_id)
        wbs_tasks = self._wbs.list_tasks(project_id)
        completed_count = sum(1 for t in wbs_tasks if t.status == "completed")
        
        # 风险登记
        risks = self._risk.get_register(project_id)
        high_risks = [r for r in risks if r.severity >= 4]
        
        # 质量指标
        quality_metrics = self._quality.get_metrics(project_id)
        
        # 进度
        progress = self._progress.get_progress(project_id)
        
        return ProjectOverview(
            project_id=project_id,
            project_name=project.get("name", ""),
            description=project.get("description", ""),
            status=project.get("status", "active"),
            progress=progress,
            start_date=project.get("start_date"),
            end_date=project.get("end_date"),
            total_tasks=len(wbs_tasks),
            completed_tasks=completed_count,
            wbs_tree=wbs_tree,
            risk_count=len(risks),
            high_risk_count=len(high_risks),
            risks=[{
                "id": r.id,
                "name": r.name,
                "severity": r.severity,
                "status": r.status,
            } for r in risks[:5]],  # 只取前5个
            quality_metrics=quality_metrics,
            budget_allocated=project.get("budget_allocated", 0),
            budget_used=project.get("budget_used", 0),
            created_at=project.get("created_at", datetime.now()),
            updated_at=project.get("updated_at", datetime.now()),
        )
    
    def get_wbs_tasks(self, project_id: str) -> List[WBSTask]:
        """获取 WBS 任务列表"""
        return self._wbs.list_tasks(project_id)
    
    def get_risks(self, project_id: str) -> List[Risk]:
        """获取风险列表"""
        return self._risk.get_register(project_id)
    
    def get_quality_metrics(self, project_id: str) -> Optional[QualityMetrics]:
        """获取质量指标"""
        return self._quality.get_metrics(project_id)
    
    def get_progress(self, project_id: str) -> float:
        """获取进度"""
        return self._progress.get_progress(project_id)
    
    # 委托给 ProjectManager 的方法
    def create_project(self, project_data: Dict[str, Any]) -> str:
        """创建项目"""
        return self._project.create(project_data)
    
    def update_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """更新项目"""
        return self._project.update(project_id, project_data)
    
    def list_projects(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出项目"""
        return self._project.list(status)
