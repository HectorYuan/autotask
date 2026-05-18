# AutoTask 技术方案

> 版本: v1.0 | 日期: 2026-05-14 | 状态: 规划中

---

## 一、技术选型

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **零依赖核心** | 核心模块仅使用 Python 标准库 |
| **可选扩展** | 高级功能通过可选依赖按需加载 |
| **渐进增强** | 从 SQLite 开始，支持 MySQL/PostgreSQL |
| **AI Ready** | 内置 LLM 适配器接口 |

### 1.2 技术栈总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            技术栈分层                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         接口层 (可选)                                 │   │
│  │  REST API: FastAPI/Flask  │  CLI: Typer  │  gRPC: grpcio          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         业务层 (标准库)                                │   │
│  │  asyncio  │  dataclasses  │  logging  │  sqlite3  │  threading     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         存储层 (可选)                                 │   │
│  │  SQLite  │  MySQL  │  PostgreSQL  │  Redis  │  SQLite+aiosqlite    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AI层 (可选)                                   │   │
│  │  OpenAI  │  Anthropic  │  LangChain  │  自定义 Adapter              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、依赖配置

### 2.1 pyproject.toml

```toml
[project]
name = "autotask"
version = "0.1.0"
description = "企业级任务编排与项目管理框架"
requires-python = ">=3.10"
license = {text = "MIT"}

[project.optional-dependencies]

# === 核心增强 ===
core = [
    "pydantic>=2.0",           # 数据验证
    "python-dotenv>=1.0",       # 环境变量
]

# === 异步支持 ===
async = [
    "aiofiles>=23.0",           # 异步文件
    "aiosqlite>=0.19",          # 异步SQLite
]

# === 数据库支持 ===
mysql = [
    "aiomysql>=0.2",            # 异步MySQL
    "sqlalchemy>=2.0",          # ORM
]
postgres = [
    "asyncpg>=0.29",            # 异步PostgreSQL
    "sqlalchemy>=2.0",
]

# === 消息队列 ===
redis = [
    "redis>=5.0",                # Redis客户端
]
celery = [
    "celery>=5.3",               # Celery
]

# === API层 ===
fastapi = [
    "fastapi>=0.109",           # FastAPI
    "uvicorn[standard]>=0.27",   # ASGI服务器
]
flask = [
    "flask>=3.0",                # Flask
]

# === CLI工具 ===
cli = [
    "typer>=0.9",                # CLI框架
    "rich>=13.0",                # 终端美化
    "click>=8.0",                # CLI组件
]

# === AI/LLM支持 ===
ai-openai = [
    "openai>=1.0",               # OpenAI
]
ai-anthropic = [
    "anthropic>=0.18",           # Anthropic
]
ai-langchain = [
    "langchain>=0.1",           # LangChain
    "langchain-openai>=0.0.5",
]

# === 监控 ===
monitoring = [
    "prometheus-client>=0.19",   # Prometheus
    "opentelemetry-api>=1.21",   # OpenTelemetry
    "opentelemetry-sdk>=1.21",
]

# === 通知 ===
notify = [
    "httpx>=0.26",               # HTTP客户端
]

# === 完整安装 ===
full = [
    "aiosqlite>=0.19",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "fastapi>=0.109",
    "uvicorn[standard]>=0.27",
    "typer>=0.9",
    "rich>=13.0",
    "redis>=5.0",
]

# === 开发依赖 ===
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "black>=23.0",
    "isort>=5.12",
    "ruff>=0.1",
]
```

---

## 三、核心实现

### 3.1 统一网关 (Gateway)

```python
# src/autotask/api/gateway.py

class AutoTaskGateway:
    """
    统一网关入口
    
    提供任务、目标、项目三大入口
    """
    
    def __init__(self, config: GatewayConfig = None):
        self._config = config or GatewayConfig()
        self._task_engine = TaskEngine(self._config)
        self._goal_manager = GoalManager(self._config)
        self._project_manager = ProjectManager(self._config)
        self._event_bus = UnifiedEventBus()
    
    # === TaskChain ===
    async def submit_task(
        self,
        title: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        executor_type: ExecutorType = ExecutorType.MAIN_AGENT,
        **kwargs
    ) -> TaskResult:
        """提交任务"""
        ...
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """查询任务状态"""
        ...
    
    # === GoalChain ===
    async def define_goal(
        self,
        title: str,
        description: str,
        milestones: List[MilestoneSpec] = None,
        **kwargs
    ) -> GoalResult:
        """定义目标"""
        ...
    
    async def create_blueprint(
        self,
        goal_id: str,
        content: BlueprintContent,
        **kwargs
    ) -> BlueprintResult:
        """创建蓝图"""
        ...
    
    # === Project ===
    async def create_project(
        self,
        name: str,
        description: str,
        **kwargs
    ) -> ProjectResult:
        """创建项目"""
        ...
```

### 3.2 任务引擎 (TaskEngine)

```python
# src/autotask/core/engine.py

class TaskEngine:
    """
    任务引擎
    
    职责：
    - 任务提交与调度
    - 优先级队列管理
    - 任务分发协调
    """
    
    def __init__(self, config: GatewayConfig):
        self._config = config
        self._queue = PriorityQueue(maxsize=config.max_queue_size)
        self._dispatcher = TaskDispatcher(config)
        self._executor_pool = ExecutorPool(config)
        self._event_bus = UnifiedEventBus()
        self._repository = TaskRepository(config)
    
    async def submit(
        self,
        task: TaskSubmission
    ) -> str:
        """提交任务，返回task_id"""
        # 1. 创建任务
        task = Task(
            id=str(uuid.uuid4()),
            title=task.title,
            payload=task.payload,
            priority=task.priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            **task.metadata
        )
        
        # 2. 持久化
        await self._repository.save(task)
        
        # 3. 加入队列
        await self._queue.put(task)
        
        # 4. 发布事件
        await self._event_bus.publish(
            EventType.TASK_CREATED,
            {"task_id": task.id}
        )
        
        return task.id
    
    async def _process_queue(self):
        """队列处理循环"""
        while True:
            task = await self._queue.get()
            try:
                result = await self._dispatcher.dispatch(task)
                await self._repository.update_result(task.id, result)
                await self._event_bus.publish(
                    EventType.TASK_COMPLETED,
                    {"task_id": task.id, "result": result}
                )
            except Exception as e:
                await self._handle_failure(task, e)
```

### 3.3 任务分发器 (Dispatcher)

```python
# src/autotask/core/dispatcher.py

class TaskDispatcher:
    """
    任务分发器
    
    职责：
    - 任务路由（选择执行器）
    - 负载均衡
    - 执行协调
    """
    
    def __init__(self, config: GatewayConfig):
        self._config = config
        self._router = TaskRouter(config)
        self._executor_pool = ExecutorPool(config)
        self._load_balancer = LoadBalancer()
    
    async def dispatch(self, task: Task) -> ExecutionResult:
        """分发任务到合适的执行器"""
        # 1. 路由选择
        executor_type = await self._router.route(task)
        
        # 2. 获取执行器
        executor = await self._load_balancer.get_executor(
            executor_type,
            self._executor_pool
        )
        
        # 3. 执行
        return await executor.execute(task)


class TaskRouter:
    """任务路由器"""
    
    ROUTING_RULES = {
        "simple": ExecutorType.SCRIPT,
        "complex": ExecutorType.CHAIN,
        "ai_agent": ExecutorType.MAIN_AGENT,
        "sub_task": ExecutorType.SUB_AGENT,
    }
    
    async def route(self, task: Task) -> ExecutorType:
        """根据任务特征路由"""
        if task.payload.get("type") in self.ROUTING_RULES:
            return self.ROUTING_RULES[task.payload["type"]]
        
        # 默认逻辑
        if task.complexity > Complexity.HIGH:
            return ExecutorType.MAIN_AGENT
        elif task.dependencies:
            return ExecutorType.CHAIN
        else:
            return ExecutorType.SCRIPT
```

### 3.4 执行器池 (ExecutorPool)

```python
# src/autotask/chain/pool.py

class ExecutorPool:
    """
    执行器池
    
    管理不同类型的执行器实例
    """
    
    def __init__(self, config: GatewayConfig):
        self._config = config
        self._executors: Dict[ExecutorType, List[Executor]] = {
            ExecutorType.MAIN_AGENT: [],
            ExecutorType.SUB_AGENT: [],
            ExecutorType.SCRIPT: [],
            ExecutorType.CHAIN: [],
        }
        self._locks: Dict[ExecutorType, asyncio.Lock] = {}
        self._initialize()
    
    def _initialize(self):
        """初始化执行器池"""
        for et in ExecutorType:
            self._locks[et] = asyncio.Lock()
            
            # 根据配置创建初始实例
            for _ in range(self._config.pool_size.get(et, 2)):
                executor = self._create_executor(et)
                self._executors[et].append(executor)
    
    def _create_executor(self, executor_type: ExecutorType) -> Executor:
        """创建执行器实例"""
        return {
            ExecutorType.MAIN_AGENT: AgentExecutor(self._config),
            ExecutorType.SUB_AGENT: SubAgentExecutor(self._config),
            ExecutorType.SCRIPT: ScriptExecutor(self._config),
            ExecutorType.CHAIN: ChainExecutor(self._config),
        }[executor_type]
    
    async def acquire(self, executor_type: ExecutorType) -> Executor:
        """获取执行器"""
        async with self._locks[executor_type]:
            executors = self._executors[executor_type]
            if executors:
                return executors.pop()
            # 扩容
            return self._create_executor(executor_type)
    
    async def release(self, executor_type: ExecutorType, executor: Executor):
        """归还执行器"""
        async with self._locks[executor_type]:
            self._executors[executor_type].append(executor)
```

### 3.5 状态机 (StateMachine)

```python
# src/autotask/core/state_machine.py

from enum import Enum
from typing import Dict, Set, Callable

class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskEvent(Enum):
    START = "start"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCEL = "cancel"
    TIMEOUT = "timeout"

class TaskStateMachine:
    """
    任务状态机
    
    管理任务状态流转
    """
    
    TRANSITIONS: Dict[TaskState, Dict[TaskEvent, TaskState]] = {
        TaskState.PENDING: {
            TaskEvent.START: TaskState.RUNNING,
            TaskEvent.CANCEL: TaskState.CANCELLED,
        },
        TaskState.RUNNING: {
            TaskEvent.SUCCESS: TaskState.COMPLETED,
            TaskEvent.FAILURE: TaskState.FAILED,
            TaskEvent.TIMEOUT: TaskState.FAILED,
            TaskEvent.CANCEL: TaskState.CANCELLED,
        },
        TaskState.FAILED: {
            TaskEvent.RETRY: TaskState.PENDING,
        },
    }
    
    def __init__(self, task_id: str):
        self._task_id = task_id
        self._state = TaskState.PENDING
        self._handlers: Dict[TaskEvent, List[Callable]] = {}
    
    @property
    def state(self) -> TaskState:
        return self._state
    
    def transition(self, event: TaskEvent) -> bool:
        """状态转换"""
        if event in self.TRANSITIONS.get(self._state, {}):
            self._state = self.TRANSITIONS[self._state][event]
            self._notify_handlers(event)
            return True
        return False
    
    def on(self, event: TaskEvent, handler: Callable):
        """注册事件处理器"""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
```

### 3.6 事件总线 (EventBus)

```python
# src/autotask/core/event_bus.py

class UnifiedEventBus:
    """
    统一事件总线
    
    支持同步/异步订阅，发布-订阅模式
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._async_subscribers: Dict[EventType, List[Coroutine]] = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """同步订阅"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    async def subscribe_async(self, event_type: EventType, handler: Coroutine):
        """异步订阅"""
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
        self._async_subscribers[event_type].append(handler)
    
    async def publish(self, event_type: EventType, data: Dict[str, Any]):
        """发布事件"""
        event = Event(type=event_type, data=data, timestamp=datetime.now())
        
        # 同步处理
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logging.error(f"Event handler error: {e}")
        
        # 异步处理
        tasks = []
        for handler in self._async_subscribers.get(event_type, []):
            tasks.append(handler(event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 四、数据模型

### 4.1 任务模型

```python
# src/autotask/models/task.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

class Priority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecutorType(Enum):
    MAIN_AGENT = "main_agent"
    SUB_AGENT = "sub_agent"
    SCRIPT = "script"
    CHAIN = "chain"

@dataclass
class Task:
    id: str
    title: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    
    executor_type: ExecutorType = ExecutorType.MAIN_AGENT
    dependencies: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    goal_id: Optional[str] = None
    project_id: Optional[str] = None
    
    retry_count: int = 0
    max_retries: int = 3
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
    
    @property
    def execution_time(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
```

### 4.2 目标模型

```python
# src/autotask/models/goal.py

@dataclass
class Goal:
    id: str
    title: str
    description: str
    
    blueprint_id: Optional[str] = None
    milestones: List[Milestone] = field(default_factory=list)
    
    progress: float = 0.0  # 0.0 ~ 1.0
    status: GoalStatus = GoalStatus.DRAFT
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Milestone:
    id: str
    title: str
    description: str
    
    target_date: Optional[datetime] = None
    status: MilestoneStatus = MilestoneStatus.PENDING
    
    tasks: List[str] = field(default_factory=list)  # task_ids
    progress: float = 0.0
```

### 4.3 项目模型

```python
# src/autotask/models/project.py

@dataclass
class Project:
    id: str
    name: str
    description: str
    
    wbs: WBS = None
    risks: List[Risk] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    
    progress: float = 0.0
    status: ProjectStatus = ProjectStatus.PLANNING
    
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class WBS:
    """工作分解结构"""
    root_id: str
    nodes: Dict[str, WBSNode] = field(default_factory=dict)

@dataclass
class WBSNode:
    id: str
    name: str
    level: int
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    progress: float = 0.0
```

---

## 五、存储层设计

### 5.1 Repository 模式

```python
# src/autotask/storage/repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """仓储抽象基类"""
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        pass
    
    @abstractmethod
    async def list(self, **filters) -> List[T]:
        pass
    
    @abstractmethod
    async def update(self, id: str, entity: T) -> T:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

class SQLiteRepository(Repository[T]):
    """SQLite仓储实现"""
    
    def __init__(self, db_path: str, model_type: type):
        self._db_path = db_path
        self._model_type = model_type
        self._conn = None
    
    async def _get_conn(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._db_path)
        return self._conn
    
    async def save(self, entity: T) -> T:
        conn = await self._get_conn()
        data = self._entity_to_dict(entity)
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' * len(data)])
        await conn.execute(
            f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})",
            tuple(data.values())
        )
        await conn.commit()
        return entity
```

---

## 六、适配器设计

### 6.1 适配器注册表

```python
# src/autotask/adapters/registry.py

class AdapterRegistry:
    """适配器注册表"""
    
    _adapters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: type):
        cls._adapters[name] = adapter_class
    
    @classmethod
    def get(cls, name: str, config: Dict[str, Any]):
        adapter_class = cls._adapters.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown adapter: {name}")
        return adapter_class(config)

# === 数据库适配器 ===
AdapterRegistry.register("sqlite", SQLiteAdapter)
AdapterRegistry.register("mysql", MySQLAdapter)
AdapterRegistry.register("postgresql", PostgreSQLAdapter)

# === LLM适配器 ===
AdapterRegistry.register("openai", OpenAIAdapter)
AdapterRegistry.register("anthropic", AnthropicAdapter)
AdapterRegistry.register("ollama", OllamaAdapter)

# === 通知适配器 ===
AdapterRegistry.register("webhook", WebhookAdapter)
AdapterRegistry.register("email", EmailAdapter)
AdapterRegistry.register("feishu", FeishuAdapter)
```

### 6.2 LLM 适配器接口

```python
# src/autotask/adapters/llm/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMAdapter(ABC):
    """
    LLM适配器基类（统一抽象接口）
    
    设计决策: 统一抽象 + 多provider支持
    - 不绑定特定provider
    - 支持 OpenAI / Anthropic / Ollama / 火山引擎等
    - 每个适配器约 200 行代码
    """
    
    def __init__(self, config: LLMConfig):
        self._config = config
    
    # === 统一接口属性 ===
    @property
    @abstractmethod
    def provider(self) -> str:
        """provider名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass
    
    @property
    def supports_tools(self) -> bool:
        """是否支持工具调用"""
        return True
    
    @property
    def supports_stream(self) -> bool:
        """是否支持流式输出"""
        return True
    
    @property
    def supports_json_mode(self) -> bool:
        """是否支持JSON模式"""
        return True
    
    # === 核心接口 ===
    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> ChatResponse:
        """聊天接口"""
        pass
    
    @abstractmethod
    async def embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """嵌入接口"""
        pass

class OpenAIAdapter(LLMAdapter):
    """OpenAI适配器"""
    
    async def chat(self, messages, **kwargs) -> ChatResponse:
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=[m.to_dict() for m in messages],
            **kwargs
        )
        return ChatResponse(
            content=response.choices[0].message.content,
            usage=response.usage,
            model=response.model,
        )
```

---

## 七、配置管理

### 7.1 配置模型

```python
# src/autotask/config.py

from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path

@dataclass
class GatewayConfig:
    """网关配置"""
    
    # 存储
    database_url: str = "sqlite:///./autotask.db"
    
    # 执行器池
    pool_size: Dict[str, int] = field(default_factory=lambda: {
        "main_agent": 2,
        "sub_agent": 5,
        "script": 3,
        "chain": 2,
    })
    
    # 任务配置
    max_queue_size: int = 1000
    default_timeout: int = 300
    max_retries: int = 3
    
    # 事件总线
    event_buffer_size: int = 100
    
    # LLM
    llm_adapter: str = "openai"
    llm_config: Dict = field(default_factory=dict)
    
    # 通知
    notify_adapters: list = field(default_factory=list)
```

### 7.2 环境变量加载

```python
# src/autotask/config.py

from dotenv import load_dotenv
from os import getenv

def load_config() -> GatewayConfig:
    """从环境变量加载配置"""
    load_dotenv()
    
    return GatewayConfig(
        database_url=getenv("DATABASE_URL", "sqlite:///./autotask.db"),
        max_queue_size=int(getenv("MAX_QUEUE_SIZE", "1000")),
        default_timeout=int(getenv("DEFAULT_TIMEOUT", "300")),
        llm_adapter=getenv("LLM_ADAPTER", "openai"),
        llm_config={
            "api_key": getenv("OPENAI_API_KEY"),
            "model": getenv("OPENAI_MODEL", "gpt-4"),
        }
    )
```

---

## 八、Workflow 预留接口 (v1预留)

> 设计决策: v1预留接口，避免后期重构

```python
# src/autotask/core/workflow.py

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

class WorkflowNodeType(Enum):
    """工作流节点类型"""
    START = "start"
    END = "end"
    TASK = "task"           # 任务节点
    GATEWAY = "gateway"     # 条件网关 [预留]
    SUBPROCESS = "subprocess"  # 子流程 [预留]

@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    type: WorkflowNodeType
    task: Optional[Any] = None  # 关联的任务
    condition: Optional[str] = None  # 条件表达式 [预留]

@dataclass
class WorkflowEdge:
    """工作流边"""
    source: str  # 源节点ID
    target: str  # 目标节点ID
    condition: Optional[str] = None  # 条件表达式 [预留]

@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    initial_node: Optional[str] = None

# === LLM适配器优先级 ===
# P0: OpenAI (功能最全，参考实现)
# P0: Anthropic (成本优化)
# P1: Ollama (私有化部署)
# P1: 火山引擎/豆包 (国内用户)
# P2: 其他 (按需扩展)
```
