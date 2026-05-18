# AutoTask 关键决策方案对比

> 决策日期: 2026-05-14 | 状态: ✅ 已确认

---

## Q1: TaskMachine 定位

### 问题
TaskMachine（`System/core/task/`）中的 TaskMachine 类保留还是重构？

### 选项对比

| 维度 | 选项A: 保留重构 | 选项B: StateMachine 替代 |
|------|------------------|-------------------------|
| **来源** | `System/core/task/state_machine.py` | 新建 `core/state_machine.py` |
| **定位** | 状态机 + 执行器工厂 | 纯粹状态机 |
| **复杂度** | 中（需解耦状态机与执行器） | 低（全新实现） |
| **工作量** | 3-5天（提取、适配） | 1-2天（重写） |
| **兼容性** | 高（保留原接口） | 低（需要迁移） |
| **可维护性** | 中（两层职责混合） | 高（单一职责） |

### 详细分析

#### 选项A: 保留重构

**来源代码结构**（`System/core/task/`）:
```python
# state_machine.py
class TaskMachine:
    """任务状态机"""
    def transition(self, event): ...
    def get_state(self): ...

# executor_factory.py
class ExecutorFactory:
    """执行器工厂"""
    def create_executor(self, task_type): ...
```

**优点**:
- 保留已有实现，减少工作量
- 兼容现有调用方
- 经过验证的逻辑

**缺点**:
- TaskMachine 类名与项目名重叠
- 状态机与执行器工厂耦合
- 需要仔细解耦

#### 选项B: StateMachine 替代

**新设计方案**:
```python
# core/state_machine.py
class StateMachine:
    """通用状态机"""
    def __init__(self, states, transitions, initial_state): ...
    def transition(self, event) -> bool: ...
    def can_transition(self, event) -> bool: ...

# core/executor_factory.py (新)
class ExecutorFactory:
    """执行器工厂（独立）"""
    def create(self, executor_type: ExecutorType) -> Executor: ...
```

**优点**:
- 单一职责，职责清晰
- 可复用为通用组件
- 更符合 Clean Architecture

**缺点**:
- 需要迁移现有代码
- 可能丢失某些边界情况处理

### 建议: **选项B - StateMachine 替代** ✅

**理由**:
1. TaskMachine 原代码约 300 行，重写成本低
2. 状态机是通用组件，应该独立
3. 新实现更符合模块化设计
4. 可以从 `System/core/task_system/core/` 中的状态机实现获取灵感

---

## Q2: ProjectContext 定位

### 问题
ProjectContext 是聚合视图还是实现类？

### 选项对比

| 维度 | 选项A: 聚合视图 | 选项B: 实现类 |
|------|-----------------|---------------|
| **职责** | 组合查询、聚合展示 | 业务逻辑、数据操作 |
| **依赖** | 依赖各 Manager | 独立或依赖 Repository |
| **复杂度** | 低（组合逻辑） | 中（业务逻辑） |
| **粒度** | 粗粒度 | 细粒度 |

### 详细分析

#### 选项A: 聚合视图

```python
# project/context.py
class ProjectContext:
    """项目上下文聚合视图"""
    
    def __init__(self, 
                 project_mgr: ProjectManager,
                 wbs_engine: WBSEngine,
                 risk_mgr: RiskManager,
                 quality_mgr: QualityManager):
        self._project = project_mgr
        self._wbs = wbs_engine
        self._risk = risk_mgr
        self._quality = quality_mgr
    
    def get_project_overview(self, project_id: str) -> ProjectOverview:
        """聚合项目全景视图"""
        project = self._project.get(project_id)
        wbs = self._wbs.get_tree(project_id)
        risks = self._risk.get_register(project_id)
        quality = self._quality.get_metrics(project_id)
        
        return ProjectOverview(
            project=project,
            wbs_tree=wbs,
            risk_register=risks,
            quality_metrics=quality,
            # 计算聚合指标
            overall_progress=self._calculate_progress(wbs, quality),
            risk_level=self._calculate_risk_level(risks),
        )
```

**优点**:
- 清晰的聚合职责
- 不重复业务逻辑
- 易测试（mock 各 Manager）

**缺点**:
- 依赖注入复杂
- 需要协调多个 Manager

#### 选项B: 实现类

```python
# project/project_context.py
class ProjectContext:
    """项目上下文（带业务逻辑）"""
    
    def __init__(self, db: Database):
        self._db = db
    
    def get_overview(self, project_id: str) -> ProjectOverview:
        # 直接查询数据库
        # 实现业务逻辑
        ...
    
    def create_wbs_node(self, parent_id: str, name: str) -> WBSNode:
        # 直接操作数据库
        ...
    
    def identify_risk(self, project_id: str, risk: Risk) -> str:
        # 直接操作数据库
        ...
```

**优点**:
- 独立性强
- 调用简单

**缺点**:
- 违反 DRY（重复 Manager 逻辑）
- 难以维护
- 难以测试

### 建议: **选项A - 聚合视图** ✅

**理由**:
1. ProjectContext 不应承担具体业务逻辑
2. 保持各 Manager 的单一职责
3. 聚合视图更符合 DDD 的 Application Service 模式
4. 便于后续拆分微服务

---

## Q3: 工作流编排支持

### 问题
是否需要支持工作流编排（如 BPMN）？

### 选项对比

| 维度 | 选项A: v1不需要 | 选项B: v1预留接口 |
|------|-----------------|-------------------|
| **复杂度** | 低 | 中 |
| **工作量增加** | 0 | +1周 |
| **扩展性** | 需后期重构 | 可平滑演进 |
| **适用场景** | 简单任务 | 复杂流程 |

### 详细分析

#### 选项A: v1不需要

**设计思路**:
```
TaskChain  ──► 简单任务编排
              ├── 顺序执行
              ├── 并行执行
              └── 依赖执行

不支持: 条件分支、循环、子流程
```

**适用场景**:
- 简单的 AI Agent 任务
- 独立的脚本执行
- 基础的目标追踪

**缺点**:
- 无法处理复杂业务流程
- 后期需要重构

#### 选项B: v1预留接口

**设计思路**:
```python
# core/workflow.py
class WorkflowEngine:
    """工作流引擎（预留）"""
    
    async def execute(self, workflow: Workflow) -> WorkflowResult:
        """执行工作流"""
        ...
    
    async def validate(self, workflow: Workflow) -> ValidationResult:
        """验证工作流定义"""
        ...

class Workflow:
    """工作流定义"""
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]  # 连接关系
    
class WorkflowNode:
    """工作流节点"""
    type: NodeType  # TASK, GATEWAY, SUBPROCESS
    task: Optional[Task]

class WorkflowEdge:
    """工作流边"""
    source: str
    target: str
    condition: Optional[str]  # 条件表达式
```

**接口预留**:
```python
# project/workflow_support.py (可选扩展)
WANTED_LATER = [
    "WorkflowEngine",
    "BPMNParser", 
    "WorkflowDesigner",
]
```

**优点**:
- 预留演进空间
- 不影响当前设计
- 未来可平滑扩展

**缺点**:
- 初期工作量略增
- 需要考虑接口兼容性

### 建议: **选项B - v1预留接口** ✅

**理由**:
1. 目标用户场景必然涉及复杂流程
2. 预留接口成本低（1-2天）
3. 避免后期大规模重构
4. 符合 "演进式架构" 原则

**预留内容**:
```python
# src/autotask/core/workflow.py
class WorkflowNode(Enum):
    TASK = "task"
    GATEWAY = "gateway"       # 预留
    SUBPROCESS = "subprocess"  # 预留
    START = "start"
    END = "end"

class WorkflowEdge:
    """预留：支持条件表达式"""
    condition: Optional[str] = None  # 如 "${task.result > 0}"
```

---

## Q4: LLM 适配器优先级

### 问题
LLM 适配器优先支持哪些 provider？

### 选项对比

| 维度 | 选项A: OpenAI | 选项B: Anthropic | 选项C: 都支持 |
|------|---------------|-------------------|---------------|
| **优先级** | 必须 | 次要 | 平等 |
| **开发成本** | 低 | 中 | 高 |
| **生态成熟度** | 高 | 高 | - |
| **成本控制** | 中 | 低 | - |
| **国内可用性** | 中（受限） | 低 | - |

### 详细分析

#### 选项A: OpenAI 优先

**适配器设计**:
```python
# adapters/llm/openai.py
class OpenAIAdapter(LLMAdapter):
    def __init__(self, config: LLMConfig):
        self._client = OpenAI(api_key=config.api_key)
        self._model = config.model or "gpt-4"
    
    async def chat(self, messages, **kwargs) -> ChatResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[m.to_dict() for m in messages],
            **kwargs
        )
        return ChatResponse(...)
```

**优点**:
- API 成熟稳定
- 功能完善（tools、json_mode、vision）
- 文档丰富

**缺点**:
- 成本较高
- 国内访问受限

#### 选项B: Anthropic 次要

**适配器设计**:
```python
# adapters/llm/anthropic.py
class AnthropicAdapter(LLMAdapter):
    def __init__(self, config: LLMConfig):
        self._client = Anthropic(api_key=config.api_key)
        self._model = config.model or "claude-3-opus"
    
    async def chat(self, messages, **kwargs) -> ChatResponse:
        response = self._client.messages.create(
            model=self._model,
            messages=[m.to_dict() for m in messages],
            **kwargs
        )
        return ChatResponse(...)
```

**优点**:
- 成本较低
- 长上下文优秀
- 安全性高

**缺点**:
- API 相对新
- 部分功能（如 tools）较晚支持

#### 选项C: 统一抽象 + 都支持

```python
# adapters/llm/base.py
class LLMAdapter(ABC):
    """统一接口"""
    
    @abstractmethod
    async def chat(self, messages, **kwargs) -> ChatResponse:
        pass
    
    @abstractmethod
    async def chat_stream(self, messages, **kwargs) -> AsyncIterator[str]:
        """流式输出（统一接口）"""
        pass
    
    @abstractmethod
    async def embeddings(self, texts, **kwargs) -> List[List[float]]:
        pass

# adapters/llm/unified.py
class UnifiedLLMAdapter(LLMAdapter):
    """统一适配器，支持多 provider"""
    
    PROVIDERS = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "ollama": OllamaAdapter,
    }
    
    def __init__(self, config: LLMConfig):
        provider = config.provider or "openai"
        self._adapter = self.PROVIDERS[provider](config)
```

### 建议: **选项C - 统一抽象 + 都支持** ✅

**理由**:
1. 统一抽象层是关键，不绑定特定 provider
2. 国内用户可能需要支持火山引擎（豆包）等
3. 企业用户可能有私有化部署需求（Ollama）
4. 适配器开发成本可控（每个 ~200行）

**推荐适配器顺序**:

| 优先级 | Provider | 原因 |
|--------|----------|------|
| P0 | OpenAI | 功能最全，参考实现 |
| P0 | Anthropic | 成本优化选项 |
| P1 | Ollama | 私有化部署 |
| P1 | 火山引擎 | 国内用户 |
| P2 | 其他 | 按需扩展 |

**统一接口设计**:
```python
# adapters/llm/base.py
class LLMAdapter(ABC):
    """LLM 适配器统一接口"""
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """provider 名称"""
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
        """是否支持 JSON 模式"""
        return True
    
    @abstractmethod
    async def chat(self, messages, **kwargs) -> ChatResponse:
        pass
    
    @abstractmethod
    async def embeddings(self, texts, **kwargs) -> List[List[float]]:
        pass
```

---

## 决策汇总

| 问题 | 建议选项 | 优先级 |
|------|----------|--------|
| Q1: TaskMachine 定位 | **B - StateMachine 替代** | 🔴 高 |
| Q2: ProjectContext 定位 | **A - 聚合视图** | 🔴 高 |
| Q3: 工作流编排 | **B - v1预留接口** | 🟡 中 |
| Q4: LLM 适配器 | **C - 统一抽象 + 都支持** | 🟡 中 |

---

## 下一步行动

| 决策 | 更新文档 | 执行时间 |
|------|----------|----------|
| Q1 | 更新 AutoTask-Arch.md 模块映射 | 确认后 5min |
| Q2 | 更新 AutoTask-Arch.md ProjectContext 定位 | 确认后 5min |
| Q3 | 在 AutoTask-Tech.md 增加 Workflow 接口 | 确认后 30min |
| Q4 | 在 AutoTask-Tech.md 完善适配器设计 | 确认后 30min |

---

> ⚠️ **请确认以上四个问题的选择方案，确认后我立即更新文档**
