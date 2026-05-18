"""
仓储模式实现
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import uuid
from pathlib import Path
import asyncio
import aiofiles


T = TypeVar("T")


@dataclass
class Entity:
    """实体基类"""
    id: str
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 处理 datetime 序列化
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """从字典创建"""
        # 处理 datetime 反序列化
        for key in ["created_at", "updated_at"]:
            if key in data and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class Repository(ABC, Generic[T]):
    """
    仓储接口
    
    定义数据的持久化操作
    """
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass
    
    @abstractmethod
    async def get(self, entity_id: str) -> Optional[T]:
        """获取实体"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def list(self, **filters) -> List[T]:
        """列出实体"""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """检查实体是否存在"""
        pass
    
    @abstractmethod
    async def count(self, **filters) -> int:
        """统计数量"""
        pass


class InMemoryRepository(Repository[T]):
    """
    内存仓储
    
    简单的内存存储实现
    """
    
    def __init__(self, entity_class: Type[T]):
        self._entity_class = entity_class
        self._entities: Dict[str, T] = {}
        self._lock = asyncio.Lock()
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        async with self._lock:
            if not hasattr(entity, "id") or not entity.id:
                entity.id = str(uuid.uuid4())
            entity.created_at = datetime.now()
            entity.updated_at = datetime.now()
            self._entities[entity.id] = entity
            return entity
    
    async def get(self, entity_id: str) -> Optional[T]:
        """获取实体"""
        return self._entities.get(entity_id)
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        async with self._lock:
            entity.updated_at = datetime.now()
            self._entities[entity.id] = entity
            return entity
    
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        async with self._lock:
            if entity_id in self._entities:
                del self._entities[entity_id]
                return True
            return False
    
    async def list(self, **filters) -> List[T]:
        """列出实体"""
        entities = list(self._entities.values())
        
        # 简单过滤
        for key, value in filters.items():
            entities = [
                e for e in entities
                if hasattr(e, key) and getattr(e, key) == value
            ]
        
        return entities
    
    async def exists(self, entity_id: str) -> bool:
        """检查实体是否存在"""
        return entity_id in self._entities
    
    async def count(self, **filters) -> int:
        """统计数量"""
        entities = await self.list(**filters)
        return len(entities)
    
    async def clear(self) -> None:
        """清空所有实体"""
        async with self._lock:
            self._entities.clear()


class FileRepository(Repository[T]):
    """
    文件仓储基类
    
    基于文件系统的持久化
    """
    
    def __init__(self, entity_class: Type[T], base_path: Path):
        self._entity_class = entity_class
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
    
    def _get_file_path(self, entity_id: str) -> Path:
        """获取实体文件路径"""
        return self._base_path / f"{entity_id}.json"
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        async with self._lock:
            if not hasattr(entity, "id") or not entity.id:
                entity.id = str(uuid.uuid4())
            entity.created_at = datetime.now()
            entity.updated_at = datetime.now()
            
            file_path = self._get_file_path(entity.id)
            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(entity.to_dict(), ensure_ascii=False))
            
            return entity
    
    async def get(self, entity_id: str) -> Optional[T]:
        """获取实体"""
        file_path = self._get_file_path(entity_id)
        if not file_path.exists():
            return None
        
        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()
            data = json.loads(content)
            return self._entity_class.from_dict(data)
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        async with self._lock:
            entity.updated_at = datetime.now()
            
            file_path = self._get_file_path(entity.id)
            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(entity.to_dict(), ensure_ascii=False))
            
            return entity
    
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        async with self._lock:
            file_path = self._get_file_path(entity_id)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
    
    async def list(self, **filters) -> List[T]:
        """列出实体"""
        entities = []
        
        async with self._lock:
            for file_path in self._base_path.glob("*.json"):
                try:
                    async with aiofiles.open(file_path, "r") as f:
                        content = await f.read()
                        data = json.loads(content)
                        entity = self._entity_class.from_dict(data)
                        
                        # 过滤
                        match = True
                        for key, value in filters.items():
                            if not hasattr(entity, key) or getattr(entity, key) != value:
                                match = False
                                break
                        
                        if match:
                            entities.append(entity)
                except Exception:
                    continue
        
        return entities
    
    async def exists(self, entity_id: str) -> bool:
        """检查实体是否存在"""
        return self._get_file_path(entity_id).exists()
    
    async def count(self, **filters) -> int:
        """统计数量"""
        entities = await self.list(**filters)
        return len(entities)


class JSONRepository(FileRepository[T]):
    """
    JSON 文件仓储
    
    存储为单个 JSON 文件（包含所有实体）
    """
    
    def __init__(self, entity_class: Type[T], file_path: Path):
        super().__init__(entity_class, file_path.parent)
        self._file_path = file_path
        self._entities: Dict[str, T] = {}
        self._lock = asyncio.Lock()
    
    def _get_file_path(self, entity_id: str = None) -> Path:
        """获取文件路径"""
        return self._file_path
    
    async def _load_all(self) -> Dict[str, T]:
        """加载所有实体"""
        if not self._file_path.exists():
            return {}
        
        async with aiofiles.open(self._file_path, "r") as f:
            content = await f.read()
            if not content:
                return {}
            
            data = json.loads(content)
            return {
                entity_id: self._entity_class.from_dict(entity_data)
                for entity_id, entity_data in data.items()
            }
    
    async def _save_all(self, entities: Dict[str, T]) -> None:
        """保存所有实体"""
        data = {
            entity_id: entity.to_dict()
            for entity_id, entity in entities.items()
        }
        async with aiofiles.open(self._file_path, "w") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        async with self._lock:
            self._entities = await self._load_all()
            
            if not hasattr(entity, "id") or not entity.id:
                entity.id = str(uuid.uuid4())
            entity.created_at = datetime.now()
            entity.updated_at = datetime.now()
            
            self._entities[entity.id] = entity
            await self._save_all(self._entities)
            
            return entity
    
    async def get(self, entity_id: str) -> Optional[T]:
        """获取实体"""
        async with self._lock:
            self._entities = await self._load_all()
            return self._entities.get(entity_id)
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        async with self._lock:
            self._entities = await self._load_all()
            entity.updated_at = datetime.now()
            self._entities[entity.id] = entity
            await self._save_all(self._entities)
            return entity
    
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        async with self._lock:
            self._entities = await self._load_all()
            if entity_id in self._entities:
                del self._entities[entity_id]
                await self._save_all(self._entities)
                return True
            return False
    
    async def list(self, **filters) -> List[T]:
        """列出实体"""
        async with self._lock:
            self._entities = await self._load_all()
            
            entities = list(self._entities.values())
            
            for key, value in filters.items():
                entities = [
                    e for e in entities
                    if hasattr(e, key) and getattr(e, key) == value
                ]
            
            return entities


# 使用示例的数据类
@dataclass
class Task(Entity):
    """任务实体"""
    name: str = ""
    description: str = ""
    status: str = "pending"
    priority: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.metadata is None:
            self.metadata = {}
