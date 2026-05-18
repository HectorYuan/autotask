"""
Storage 模块 - 仓储模式
"""

from autotask.storage.repository import (
    Repository,
    InMemoryRepository,
    FileRepository,
    JSONRepository,
)

__all__ = [
    "Repository",
    "InMemoryRepository",
    "FileRepository",
    "JSONRepository",
]
