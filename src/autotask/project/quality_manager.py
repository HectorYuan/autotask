"""
质量管理器
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class QualityLevel(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QualityMetrics:
    """
    质量指标
    
    包含项目各类质量度量
    """
    project_id: str
    
    # 代码质量
    code_coverage: float = 0.0  # 代码覆盖率 %
    code_complexity: float = 0.0  # 平均圈复杂度
    code_duplication: float = 0.0  # 代码重复率 %
    
    # 缺陷指标
    defect_count: int = 0
    open_defects: int = 0
    critical_defects: int = 0
    defect_density: float = 0.0  # 缺陷密度 (每千行代码)
    
    # 性能指标
    avg_response_time: float = 0.0  # 平均响应时间 ms
    error_rate: float = 0.0  # 错误率 %
    availability: float = 100.0  # 可用性 %
    
    # 流程指标
    code_review_coverage: float = 0.0  # 代码评审覆盖率 %
    test_pass_rate: float = 100.0  # 测试通过率 %
    
    # 综合评分
    overall_score: float = 0.0  # 0-100
    
    # 时间戳
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def quality_level(self) -> QualityLevel:
        """质量等级"""
        score = self.overall_score
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.POOR
        return QualityLevel.CRITICAL
    
    def calculate_overall(self) -> float:
        """计算综合评分"""
        # 加权平均
        weights = {
            "code_coverage": 0.15,
            "code_complexity": 0.10,
            "code_duplication": 0.10,
            "test_pass_rate": 0.20,
            "error_rate": 0.15,
            "code_review_coverage": 0.15,
            "availability": 0.15,
        }
        
        # 归一化各指标到 0-100
        coverage_score = min(self.code_coverage, 100)
        complexity_score = max(0, 10 - self.code_complexity) * 10  # 假设 10 以下为优秀
        duplication_score = max(0, 20 - self.code_duplication) * 5  # 假设 20% 以下为优秀
        test_score = self.test_pass_rate
        error_score = max(0, 100 - self.error_rate * 10)  # 假设 10% 以下为优秀
        review_score = self.code_review_coverage
        availability_score = self.availability
        
        scores = {
            "code_coverage": coverage_score,
            "code_complexity": complexity_score,
            "code_duplication": duplication_score,
            "test_pass_rate": test_score,
            "error_rate": error_score,
            "code_review_coverage": review_score,
            "availability": availability_score,
        }
        
        total = sum(weights[k] * scores[k] for k in weights)
        self.overall_score = total
        return total


@dataclass
class QualityCheck:
    """质量检查项"""
    id: str
    project_id: str
    check_type: str  # unit_test, integration_test, code_review, security_scan
    name: str
    status: str  # pending, passed, failed, skipped
    passed_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    details: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class QualityManager:
    """
    质量管理器
    
    职责：
    - 收集质量指标
    - 执行质量检查
    - 生成质量报告
    """
    
    def __init__(self):
        self._metrics: Dict[str, QualityMetrics] = {}
        self._checks: Dict[str, QualityCheck] = {}
        self._project_checks: Dict[str, List[str]] = {}
    
    def get_metrics(self, project_id: str) -> Optional[QualityMetrics]:
        """
        获取质量指标
        
        Args:
            project_id: 项目 ID
            
        Returns:
            质量指标（不存在则创建空指标）
        """
        if project_id not in self._metrics:
            self._metrics[project_id] = QualityMetrics(project_id=project_id)
        return self._metrics[project_id]
    
    def update_metrics(
        self,
        project_id: str,
        metrics_data: Dict[str, Any]
    ) -> QualityMetrics:
        """
        更新质量指标
        
        Args:
            project_id: 项目 ID
            metrics_data: 指标数据
            
        Returns:
            更新后的质量指标
        """
        metrics = self.get_metrics(project_id)
        for key, value in metrics_data.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        metrics.updated_at = datetime.now()
        metrics.calculate_overall()
        return metrics
    
    def record_check(
        self,
        project_id: str,
        check_type: str,
        name: str,
        status: str,
        passed_count: int = 0,
        failed_count: int = 0,
        **kwargs
    ) -> str:
        """
        记录质量检查
        
        Args:
            project_id: 项目 ID
            check_type: 检查类型
            name: 检查名称
            status: 状态
            passed_count: 通过数
            failed_count: 失败数
            
        Returns:
            检查 ID
        """
        check_id = str(uuid.uuid4())
        
        check = QualityCheck(
            id=check_id,
            project_id=project_id,
            check_type=check_type,
            name=name,
            status=status,
            passed_count=passed_count,
            failed_count=failed_count,
            total_count=passed_count + failed_count,
            **kwargs
        )
        
        self._checks[check_id] = check
        
        if project_id not in self._project_checks:
            self._project_checks[project_id] = []
        self._project_checks[project_id].append(check_id)
        
        # 更新指标
        self._update_from_check(project_id, check)
        
        return check_id
    
    def _update_from_check(self, project_id: str, check: QualityCheck) -> None:
        """从检查结果更新指标"""
        metrics = self.get_metrics(project_id)
        
        if check.check_type == "unit_test":
            if check.total_count > 0:
                metrics.test_pass_rate = (check.passed_count / check.total_count) * 100
        
        metrics.updated_at = datetime.now()
        metrics.calculate_overall()
    
    def get_checks(
        self,
        project_id: str,
        check_type: Optional[str] = None
    ) -> List[QualityCheck]:
        """获取质量检查列表"""
        check_ids = self._project_checks.get(project_id, [])
        checks = [self._checks[cid] for cid in check_ids if cid in self._checks]
        
        if check_type:
            checks = [c for c in checks if c.check_type == check_type]
        
        return checks
    
    def get_failed_checks(self, project_id: str) -> List[QualityCheck]:
        """获取失败的检查"""
        checks = self.get_checks(project_id)
        return [c for c in checks if c.status == "failed"]
    
    def generate_report(self, project_id: str) -> Dict[str, Any]:
        """
        生成质量报告
        
        Args:
            project_id: 项目 ID
            
        Returns:
            质量报告数据
        """
        metrics = self.get_metrics(project_id)
        checks = self.get_checks(project_id)
        
        return {
            "project_id": project_id,
            "generated_at": datetime.now().isoformat(),
            "overall_score": metrics.overall_score,
            "quality_level": metrics.quality_level.value,
            "metrics": {
                "code_coverage": metrics.code_coverage,
                "test_pass_rate": metrics.test_pass_rate,
                "error_rate": metrics.error_rate,
                "availability": metrics.availability,
                "code_review_coverage": metrics.code_review_coverage,
            },
            "defects": {
                "total": metrics.defect_count,
                "open": metrics.open_defects,
                "critical": metrics.critical_defects,
            },
            "checks_summary": {
                "total": len(checks),
                "passed": len([c for c in checks if c.status == "passed"]),
                "failed": len([c for c in checks if c.status == "failed"]),
            },
            "recommendations": self._generate_recommendations(metrics, checks),
        }
    
    def _generate_recommendations(
        self,
        metrics: QualityMetrics,
        checks: List[QualityCheck]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if metrics.code_coverage < 80:
            recommendations.append(f"代码覆盖率不足 (当前 {metrics.code_coverage:.1f}%)，建议提升至 80% 以上")
        
        if metrics.test_pass_rate < 95:
            recommendations.append(f"测试通过率偏低 (当前 {metrics.test_pass_rate:.1f}%)，建议修复失败的测试")
        
        if metrics.error_rate > 1:
            recommendations.append(f"错误率偏高 (当前 {metrics.error_rate:.2f}%)，建议排查并修复问题")
        
        failed_checks = [c for c in checks if c.status == "failed"]
        if failed_checks:
            recommendations.append(f"存在 {len(failed_checks)} 个失败的质量检查，需要关注")
        
        if metrics.availability < 99:
            recommendations.append(f"可用性偏低 (当前 {metrics.availability:.1f}%)，建议提升服务稳定性")
        
        if not recommendations:
            recommendations.append("质量指标良好，继续保持")
        
        return recommendations
