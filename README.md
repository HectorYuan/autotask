# AutoTask - 智能任务自动化框架

## 项目概述

AutoTask 是一个智能任务自动化框架，支持多层级 Agent 协作、灵活的工作流编排和统一的任务管理。

## 架构设计

### 核心模块

```
DevSpace/autotask/src/autotask/
├── core/               # 核心组件
│   ├── state_machine.py      # 通用状态机（替代 TaskMachine）
│   ├── executor.py           # 执行器基类
│   ├── executor_factory.py   # 执行器工厂
│   ├── task_engine.py        # 任务引擎
│   ├── dispatcher.py         # 任务分发器
│   ├── event_bus.py          # 事件总线
│   └── workflow.py           # Workflow 预留接口
├── adapters/           # 外部适配器
│   └── llm/                   # LLM 适配器
│       ├── base.py            # 统一适配器接口
│       ├── openai_adapter.py  # OpenAI 适配器 P0
│       ├── anthropic_adapter.py # Anthropic 适配器 P0
│       └── ollama_adapter.py   # Ollama 适配器 P1
├── project/           # 项目管理
│   ├── project_context.py     # 项目上下文聚合视图
│   ├── wbs_engine.py          # WBS 分解引擎
│   ├── risk_manager.py        # 风险管理
│   ├── quality_manager.py     # 质量管理
│   └── progress_tracker.py    # 进度追踪
├── goal/              # 目标管理
│   ├── goal_manager.py        # 目标管理
│   └── milestone_tracker.py   # 里程碑追踪
├── api/               # API 网关
│   └── gateway.py             # 统一网关
└── storage/           # 仓储模式
    └── repository.py         # 仓储实现
```

### 设计决策

| 决策 | 选项 | 说明 |
|------|------|------|
| Q1: TaskMachine定位 | B - StateMachine替代 | 新建 core/state_machine.py |
| Q2: ProjectContext定位 | A - 聚合视图 | 不承担业务逻辑 |
| Q3: 工作流编排 | B - v1预留接口 | 预留演进空间 |
| Q4: LLM适配器 | C - 统一抽象+多provider | OpenAI/Anthropic优先 |

## 快速开始

### 安装

```bash
pip install -e ./DevSpace/autotask
```

### 基本使用

```python
from autotask import AutoTaskConfig, StateMachine, ExecutorFactory

# 配置
config = AutoTaskConfig.from_env()

# 创建状态机
from autotask.core.state_machine import Transition, State
transitions = [
    Transition(State.PENDING, "start", State.RUNNING),
    Transition(State.RUNNING, "complete", State.COMPLETED),
]
sm = StateMachine(
    states={State.PENDING, State.RUNNING, State.COMPLETED},
    transitions=transitions,
    initial_state=State.PENDING,
)

# 创建执行器
executor = ExecutorFactory.create("main_agent")
```

### LLM 适配器使用

```python
from autotask.adapters.llm import LLMConfig, LLMMessage, MessageRole, AdapterRegistry

# 创建配置
config = LLMConfig(model="gpt-4")

# 使用 OpenAI
openai_adapter = AdapterRegistry.get("openai", config)
response = await openai_adapter.chat([
    LLMMessage(role=MessageRole.USER, content="Hello!")
])

# 切换到 Anthropic
anthropic_adapter = AdapterRegistry.get("anthropic", config)
```

## 关键特性

### 1. 通用状态机 (StateMachine)

```python
from autotask.core.state_machine import StateMachine, Transition

transitions = [
    Transition("idle", "start", "running"),
    Transition("running", "success", "completed"),
    Transition("running", "fail", "failed"),
]

sm = StateMachine(
    states={"idle", "running", "completed", "failed"},
    transitions=transitions,
    initial_state="idle",
)

sm.transition("start")  # -> True
sm.can_transition("success")  # -> True
```

### 2. 执行器工厂 (ExecutorFactory)

```python
from autotask.core.executor_factory import ExecutorFactory, ExecutorType

# 创建执行器
main_executor = ExecutorFactory.create(ExecutorType.MAIN_AGENT)
sub_executor = ExecutorFactory.create(ExecutorType.SUB_AGENT)
script_executor = ExecutorFactory.create(ExecutorType.SCRIPT)

# 自定义执行器注册
class CustomExecutor(Executor):
    ...

ExecutorFactory.register(ExecutorType("custom"), CustomExecutor)
```

### 3. 项目上下文聚合视图 (ProjectContext)

```python
from autotask.project import ProjectContext

# 创建上下文
ctx = ProjectContext(
    project_mgr=project_mgr,
    wbs_engine=wbs_engine,
    risk_mgr=risk_mgr,
    quality_mgr=quality_mgr,
)

# 获取聚合视图
overview = ctx.get_project_overview("project-123")
```

### 4. LLM 适配器

```python
from autotask.adapters.llm import AdapterRegistry

# 注册新适配器
AdapterRegistry.register("custom", CustomLLMAdapter)

# 使用
adapter = AdapterRegistry.get("openai", config)
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码规范

```bash
ruff check src/
mypy src/
```

## 版本

当前版本: 0.1.0

## License

MIT
