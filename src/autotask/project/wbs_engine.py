"""
WBS 工作分解结构引擎
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class WBSTaskStatus(str, Enum):
    """WBS 任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class WBSTask:
    """WBS 任务"""
    id: str
    project_id: str
    name: str
    description: str = ""
    parent_id: Optional[str] = None
    level: int = 0  # 层级，0 为根
    status: WBSTaskStatus = WBSTaskStatus.PENDING
    priority: int = 0
    assigned_to: Optional[str] = None
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务 ID
    children: List[str] = field(default_factory=list)  # 子任务 ID
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class WBSEngine:
    """
    WBS 分解引擎
    
    职责：
    - 创建和管理 WBS 任务结构
    - 任务分解
    - 依赖关系管理
    """
    
    def __init__(self):
        self._tasks: Dict[str, WBSTask] = {}
        self._project_tasks: Dict[str, set] = {}  # project_id -> set of task_ids
    
    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        创建 WBS 任务
        
        Args:
            project_id: 项目 ID
            name: 任务名称
            description: 任务描述
            parent_id: 父任务 ID
            **kwargs: 其他属性
            
        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        
        # 确定层级
        level = 0
        if parent_id and parent_id in self._tasks:
            level = self._tasks[parent_id].level + 1
        
        task = WBSTask(
            id=task_id,
            project_id=project_id,
            name=name,
            description=description,
            parent_id=parent_id,
            level=level,
            **kwargs
        )
        
        self._tasks[task_id] = task
        
        # 添加到项目任务集合
        if project_id not in self._project_tasks:
            self._project_tasks[project_id] = set()
        self._project_tasks[project_id].add(task_id)
        
        # 添加到父任务的子任务列表
        if parent_id and parent_id in self._tasks:
            self._tasks[parent_id].children.append(task_id)
        
        return task_id
    
    def decompose(
        self,
        project_id: str,
        root_task_id: str,
        subtasks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        分解任务
        
        Args:
            project_id: 项目 ID
            root_task_id: 根任务 ID
            subtasks: 子任务定义列表
            
        Returns:
            创建的子任务 ID 列表
        """
        task_ids = []
        for subtask_def in subtasks:
            task_id = self.create_task(
                project_id=project_id,
                parent_id=root_task_id,
                **subtask_def
            )
            task_ids.append(task_id)
        return task_ids
    
    def get_task(self, task_id: str) -> Optional[WBSTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def update_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """更新任务"""
        if task_id in self._tasks:
            task_data["updated_at"] = datetime.now()
            self._tasks[task_id].__dict__.update(task_data)
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务（同时删除子任务）"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        
        # 递归删除子任务
        for child_id in task.children.copy():
            self.delete_task(child_id)
        
        # 从父任务中移除
        if task.parent_id and task.parent_id in self._tasks:
            parent = self._tasks[task.parent_id]
            if task_id in parent.children:
                parent.children.remove(task_id)
        
        # 从项目任务集合中移除
        if task.project_id in self._project_tasks:
            self._project_tasks[task.project_id].discard(task_id)
        
        del self._tasks[task_id]
        return True
    
    def list_tasks(self, project_id: str) -> List[WBSTask]:
        """列出项目的所有任务"""
        task_ids = self._project_tasks.get(project_id, set())
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]
    
    def get_tree(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 WBS 树结构
        
        Args:
            project_id: 项目 ID
            
        Returns:
            树形结构字典
        """
        tasks = self.list_tasks(project_id)
        if not tasks:
            return None
        
        # 找到根任务（level=0 且无父任务）
        root_tasks = [t for t in tasks if t.level == 0]
        if not root_tasks:
            return None
        
        def build_tree(task: WBSTask) -> Dict[str, Any]:
            return {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "status": task.status,
                "level": task.level,
                "children": [build_tree(self._tasks[cid]) for cid in task.children if cid in self._tasks],
            }
        
        if len(root_tasks) == 1:
            return build_tree(root_tasks[0])
        else:
            return {
                "id": project_id,
                "name": "Project Root",
                "children": [build_tree(t) for t in root_tasks],
            }
    
    def get_descendants(self, task_id: str) -> List[WBSTask]:
        """获取任务的所有后代"""
        descendants = []
        task = self._tasks.get(task_id)
        if not task:
            return descendants
        
        for child_id in task.children:
            child = self._tasks.get(child_id)
            if child:
                descendants.append(child)
                descendants.extend(self.get_descendants(child_id))
        
        return descendants
    
    def get_ancestors(self, task_id: str) -> List[WBSTask]:
        """获取任务的所有祖先"""
        ancestors = []
        task = self._tasks.get(task_id)
        if not task:
            return ancestors
        
        current = task
        while current.parent_id:
            parent = self._tasks.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break
        
        return ancestors
    
    def calculate_progress(self, task_id: str) -> float:
        """
        计算任务进度
        
        递归计算子任务的平均进度
        
        Args:
            task_id: 任务 ID
            
        Returns:
            进度百分比 (0-100)
        """
        task = self._tasks.get(task_id)
        if not task:
            return 0.0
        
        if not task.children:
            # 叶子节点，根据状态计算
            if task.status == WBSTaskStatus.COMPLETED:
                return 100.0
            elif task.status == WBSTaskStatus.IN_PROGRESS:
                if task.estimated_hours > 0:
                    return (task.actual_hours / task.estimated_hours) * 100
                return 50.0
            return 0.0
        
        # 非叶子节点，计算子任务平均进度
        total_progress = 0.0
        for child_id in task.children:
            total_progress += self.calculate_progress(child_id)
        
        return total_progress / len(task.children) if task.children else 0.0
    
    def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """
        添加依赖关系
        
        Args:
            task_id: 任务 ID
            depends_on_id: 依赖的任务 ID
            
        Returns:
            是否成功
        """
        if task_id not in self._tasks or depends_on_id not in self._tasks:
            return False
        
        if depends_on_id not in self._tasks[task_id].dependencies:
            self._tasks[task_id].dependencies.append(depends_on_id)
            return True
        return False
    
    def get_ready_tasks(self, project_id: str) -> List[WBSTask]:
        """
        获取可执行的任务
        
        可执行 = 所有依赖已完成且未被阻塞
        
        Args:
            project_id: 项目 ID
            
        Returns:
            可执行任务列表
        """
        tasks = self.list_tasks(project_id)
        ready = []
        
        for task in tasks:
            if task.status != WBSTaskStatus.PENDING:
                continue
            
            # 检查依赖是否都完成
            deps_completed = all(
                self._tasks[dep_id].status == WBSTaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self._tasks
            )
            
            if deps_completed:
                ready.append(task)
        
        return ready
