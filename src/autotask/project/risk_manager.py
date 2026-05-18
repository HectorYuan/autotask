"""
风险管理器
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class RiskSeverity(int, Enum):
    """风险严重程度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    BLOCKING = 5


class RiskStatus(str, Enum):
    """风险状态"""
    IDENTIFIED = "identified"
    ANALYZED = "analyzed"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"
    CLOSED = "closed"


@dataclass
class Risk:
    """风险项"""
    id: str
    project_id: str
    name: str
    description: str
    severity: int  # 1-5
    probability: float  # 0-1
    impact: float  # 0-1
    status: RiskStatus = RiskStatus.IDENTIFIED
    category: str = ""  # 技术/人员/业务/外部
    owner: Optional[str] = None
    mitigation_plan: str = ""
    contingency_plan: str = ""
    triggers: List[str] = field(default_factory=list)  # 触发条件
    indicators: Dict[str, Any] = field(default_factory=dict)  # 监控指标
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def score(self) -> float:
        """风险评分 = 严重程度 * 概率 * 影响"""
        return self.severity * self.probability * self.impact
    
    @property
    def level(self) -> str:
        """风险等级"""
        score = self.score
        if score >= 15:
            return "BLOCKING"
        elif score >= 10:
            return "CRITICAL"
        elif score >= 6:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        return "LOW"


class RiskManager:
    """
    风险管理器
    
    职责：
    - 风险识别
    - 风险评估
    - 风险应对计划
    - 风险监控
    """
    
    def __init__(self):
        self._risks: Dict[str, Risk] = {}
        self._project_risks: Dict[str, set] = {}  # project_id -> set of risk_ids
    
    def register(
        self,
        project_id: str,
        name: str,
        description: str,
        severity: int,
        probability: float = 0.5,
        impact: float = 0.5,
        **kwargs
    ) -> str:
        """
        注册风险
        
        Args:
            project_id: 项目 ID
            name: 风险名称
            description: 风险描述
            severity: 严重程度 (1-5)
            probability: 发生概率 (0-1)
            impact: 影响程度 (0-1)
            **kwargs: 其他属性
            
        Returns:
            风险 ID
        """
        risk_id = str(uuid.uuid4())
        
        risk = Risk(
            id=risk_id,
            project_id=project_id,
            name=name,
            description=description,
            severity=severity,
            probability=probability,
            impact=impact,
            **kwargs
        )
        
        self._risks[risk_id] = risk
        
        if project_id not in self._project_risks:
            self._project_risks[project_id] = set()
        self._project_risks[project_id].add(risk_id)
        
        return risk_id
    
    def get(self, risk_id: str) -> Optional[Risk]:
        """获取风险"""
        return self._risks.get(risk_id)
    
    def update(self, risk_id: str, risk_data: Dict[str, Any]) -> bool:
        """更新风险"""
        if risk_id in self._risks:
            risk_data["updated_at"] = datetime.now()
            self._risks[risk_id].__dict__.update(risk_data)
            return True
        return False
    
    def resolve(self, risk_id: str, resolution: str = "") -> bool:
        """
        解决风险
        
        Args:
            risk_id: 风险 ID
            resolution: 解决方案描述
            
        Returns:
            是否成功
        """
        if risk_id in self._risks:
            risk = self._risks[risk_id]
            risk.status = RiskStatus.RESOLVED
            risk.resolved_at = datetime.now()
            risk.metadata["resolution"] = resolution
            risk.updated_at = datetime.now()
            return True
        return False
    
    def close(self, risk_id: str) -> bool:
        """关闭风险"""
        if risk_id in self._risks:
            self._risks[risk_id].status = RiskStatus.CLOSED
            self._risks[risk_id].updated_at = datetime.now()
            return True
        return False
    
    def get_register(self, project_id: str) -> List[Risk]:
        """
        获取风险登记册
        
        Args:
            project_id: 项目 ID
            
        Returns:
            风险列表（按评分降序）
        """
        risk_ids = self._project_risks.get(project_id, set())
        risks = [self._risks[rid] for rid in risk_ids if rid in self._risks]
        return sorted(risks, key=lambda r: r.score, reverse=True)
    
    def get_high_risks(self, project_id: str) -> List[Risk]:
        """获取高风险列表"""
        risks = self.get_register(project_id)
        return [r for r in risks if r.score >= 10]
    
    def get_by_status(self, project_id: str, status: RiskStatus) -> List[Risk]:
        """按状态获取风险"""
        risks = self.get_register(project_id)
        return [r for r in risks if r.status == status]
    
    def get_by_category(self, project_id: str, category: str) -> List[Risk]:
        """按类别获取风险"""
        risk_ids = self._project_risks.get(project_id, set())
        return [
            self._risks[rid] for rid in risk_ids
            if rid in self._risks and self._risks[rid].category == category
        ]
    
    def calculate_risk_exposure(self, project_id: str) -> float:
        """
        计算项目风险敞口
        
        Args:
            project_id: 项目 ID
            
        Returns:
            风险敞口总额
        """
        risks = self.get_register(project_id)
        # 只计算未解决的风险
        active_risks = [r for r in risks if r.status not in [RiskStatus.RESOLVED, RiskStatus.CLOSED]]
        return sum(r.score for r in active_risks)
    
    def create_mitigation_plan(
        self,
        risk_id: str,
        plan: str,
        contingency: str = ""
    ) -> bool:
        """
        创建风险应对计划
        
        Args:
            risk_id: 风险 ID
            plan: 应对计划
            contingency: 应急计划
            
        Returns:
            是否成功
        """
        if risk_id in self._risks:
            risk = self._risks[risk_id]
            risk.mitigation_plan = plan
            risk.contingency_plan = contingency
            risk.status = RiskStatus.MITIGATING
            risk.updated_at = datetime.now()
            return True
        return False
    
    def add_trigger(self, risk_id: str, trigger: str) -> bool:
        """添加触发条件"""
        if risk_id in self._risks:
            if trigger not in self._risks[risk_id].triggers:
                self._risks[risk_id].triggers.append(trigger)
            return True
        return False
    
    def update_indicators(self, risk_id: str, indicators: Dict[str, Any]) -> bool:
        """更新监控指标"""
        if risk_id in self._risks:
            self._risks[risk_id].indicators.update(indicators)
            self._risks[risk_id].updated_at = datetime.now()
            return True
        return False
    
    def export_register(self, project_id: str) -> List[Dict[str, Any]]:
        """
        导出风险登记册
        
        Args:
            project_id: 项目 ID
            
        Returns:
            风险登记册数据
        """
        risks = self.get_register(project_id)
        return [
            {
                "id": r.id,
                "name": r.name,
                "severity": r.severity,
                "probability": r.probability,
                "impact": r.impact,
                "score": r.score,
                "level": r.level,
                "status": r.status.value,
                "owner": r.owner,
                "category": r.category,
                "mitigation_plan": r.mitigation_plan,
                "created_at": r.created_at.isoformat(),
            }
            for r in risks
        ]
