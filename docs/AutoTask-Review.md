# AutoTask 方案统一评审报告

> 评审日期: 2026-05-14 | 评审人: AI助手 | 状态: 待确认

---

## 一、评审范围

| 文档 | 版本 | 状态 |
|------|------|------|
| AutoTask-Arch.md | v1.0 | 规划中 |
| AutoTask-Tech.md | v1.0 | 规划中 |
| AutoTask-Roadmap.md | v1.0 | 规划中 |

---

## 二、整体评价

### 2.1 优点

| 维度 | 评价 |
|------|------|
| **完整性** | ✅ 三文档覆盖架构、技术、实现三大维度 |
| **架构清晰** | ✅ 双链路设计合理，TaskChain + GoalChain 解耦 |
| **技术选型** | ✅ 零依赖核心 + 可选扩展，符合设计目标 |
| **可执行性** | ✅ 8周计划有明确里程碑和验收标准 |

### 2.2 主要问题

| 优先级 | 问题 | 文档 |
|--------|------|------|
| 🔴 高 | **模块映射不完整** - TaskMachine 的 TaskMachine 和 ExecutorFactory 如何映射未明确 | Arch |
| 🔴 高 | **存储层实现缺失** - Tech 中 SQLiteRepository 未完整实现 | Tech |
| 🟡 中 | **链路集成细节不足** - TaskChain ↔ GoalChain 如何联动未详细说明 | Arch |
| 🟡 中 | **测试策略缺失** - 未说明如何验证两条链路的正确性 | Roadmap |
| 🟡 中 | **代码量估算偏保守** - 1.25万行可能低估了适配器工作量 | Roadmap |
| 🟢 低 | **文档格式可优化** - 部分代码块缺少语法高进 | All |

---

## 三、各文档详细评审

### 3.1 AutoTask-Arch.md

#### ✅ 优点
- 架构图清晰，层次分明
- 功能重叠矩阵有效说明了整合价值
- 状态流转图直观

#### ⚠️ 问题

**问题1: TaskMachine 定位模糊**

当前描述：
```
| TaskMachine | `System/core/task/` | 状态机 + 执行器 | TaskMachine、ExecutorFactory、状态机 |
```

问题：
- `TaskMachine` 既是模块名又是类名，易混淆
- `ExecutorFactory` 在 Arch 中出现两次（core/engine + chain/）

建议：
```
| TaskMachine | `System/core/task/` | 任务执行层 | TaskMachine(状态机) + ExecutorFactory(执行器工厂) → chain/ |
```

**问题2: 双链路集成点不明确**

当前：
```
              └─────────────┬───────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  ProjectContext │
```

问题：
- TaskChain 的任务完成后如何触发 GoalChain 的里程碑？
- GoalChain 的目标变更如何影响 TaskChain 的任务？

建议补充：
```
TaskChain ──► [任务完成事件] ──► GoalChain
GoalChain ──► [目标变更事件] ──► TaskChain
```

**问题3: 目录结构与模块映射不完全匹配**

Arch 目录：
```
├── goal/
│   ├── manager.py               # 目标管理器
│   ├── blueprint.py             # 蓝图引擎
│   ├── milestone.py             # 里程碑追踪
│   ├── proposal.py               # 提案管理
│   ├── review.py                 # 评审引擎
│   └── knowledge.py               # 知识库
```

来源模块：
- ProposalOS → proposal + review + knowledge
- Cultivating → goal + milestone

**问题4: ProjectContext 职责边界不清**

Arch 中 ProjectContext 包含 WBS/风险/质量管理，但 Roadmap 中 WBS 属于 project/wbs.py，Risk 属于 project/risk.py。

建议明确 ProjectContext 是聚合视图，不直接实现功能。

---

### 3.2 AutoTask-Tech.md

#### ✅ 优点
- 技术栈分层清晰
- 依赖配置完整
- 核心代码实现有价值

#### ⚠️ 问题

**问题1: 配置管理不完整**

Tech 中的 GatewayConfig 缺少：
```python
# 缺失项
class GatewayConfig:
    # ...
    log_level: str = "INFO"              # 日志级别
    log_file: Optional[str] = None      # 日志文件
    max_concurrent_tasks: int = 100     # 最大并发
    task_timeout_default: int = 300      # 默认超时
    event_queue_size: int = 1000         # 事件队列大小
    health_check_interval: int = 60      # 健康检查间隔
```

**问题2: 异常体系未定义**

Tech 未说明：
- 自定义异常类层次
- 异常与状态机的联动（如 RetryEngine 如何处理 FAILED）

建议补充：
```python
class AutoTaskException(Exception): pass
class TaskException(AutoTaskException): pass
class TaskNotFoundError(TaskException): pass
class TaskExecutionError(TaskException): pass
class RetryExhaustedError(TaskException): pass
```

**问题3: LLM 适配器接口不够通用**

当前 OpenAIAdapter 直接硬编码：
```python
response = await self._client.chat.completions.create(...)
```

问题：
- 不支持流式输出
- 不支持工具调用（function calling）
- 不支持 JSON mode

建议扩展：
```python
async def chat(
    self,
    messages: List[ChatMessage],
    tools: List[Tool] = None,       # 工具定义
    stream: bool = False,              # 流式输出
    json_mode: bool = False,           # JSON模式
    **kwargs
) -> ChatResponse:
```

---

### 3.3 AutoTask-Roadmap.md

#### ✅ 优点
- 8周计划可行
- 里程碑清晰
- 验收标准明确

#### ⚠️ 问题

**问题1: Phase 1 缺少依赖管理**

Phase 1 第1天任务：
```
├── [ ] 创建项目目录结构
├── [ ] 初始化 pyproject.toml
```

但没有包含：
```
├── [ ] 实现依赖注入机制
├── [ ] 配置加载器
├── [ ] 日志初始化
```

这些是核心架构的基础设施，应在 Phase 1 完成。

**问题2: 测试策略缺失**

当前 Roadmap 没有：
- 单元测试框架选择（pytest ✓）
- 集成测试策略
- E2E 测试策略
- 测试覆盖率目标

建议补充：
```
Phase 1 增加:
├── [ ] 配置 pytest
├── [ ] 实现 fixtures
├── [ ] 单元测试 > 80%
├── [ ] 集成测试 > 60%
```

**问题3: 代码量估算**

当前估算 ~12500 行，建议分阶段：

| 阶段 | 估算行数 | 说明 |
|------|----------|------|
| MVP (Phase 1) | 3000 | 核心骨架 |
| Beta (Phase 1+2) | 6000 | TaskChain + GoalChain |
| Release (Phase 1+2+3) | 10000 | 完整功能 |
| Stable (Phase 4) | 12500 | 含测试、文档 |

---

## 四、跨文档一致性问题

| 问题 | 涉及文档 |
|------|----------|
| TaskMachine 定位（状态机 vs 执行器） | Arch ↔ Tech |
| ProjectContext 职责（聚合 vs 实现） | Arch ↔ Roadmap |
| 验收标准中的覆盖率目标 | Roadmap ↔ Tech |
| LLM 适配器是否支持工具调用 | Tech ↔ Roadmap |

---

## 五、建议修正

### 5.1 紧急修正（执行前必须完成）

| # | 修正项 | 负责文档 |
|---|--------|----------|
| 1 | 明确 TaskMachine → TaskStateMachine + ExecutorFactory 的映射关系 | Arch |
| 2 | 补充 EventBus → TaskChain/GoalChain 的事件订阅关系图 | Arch |
| 3 | 在 Phase 1 增加依赖注入、日志配置任务 | Roadmap |
| 4 | 定义完整的异常体系 | Tech |

### 5.2 重要优化（执行中完善）

| # | 优化项 | 负责文档 |
|---|--------|----------|
| 5 | LLM 适配器增加 tools/stream/json_mode 支持 | Tech |
| 6 | 增加测试策略章节（覆盖率目标、测试类型） | Roadmap |
| 7 | 细化代码量估算，按阶段划分 | Roadmap |
| 8 | 补充 GatewayConfig 完整字段 | Tech |

### 5.3 建议补充（可选）

| # | 补充项 | 负责文档 |
|---|--------|----------|
| 9 | 性能基准测试计划 | Roadmap |
| 10 | 安全考虑（如输入验证、权限控制） | Tech |
| 11 | 国际化/本地化策略 | - |
| 12 | 监控指标定义 | Tech |

---

## 六、决策事项

### 6.1 需要明确的问题

| # | 问题 | 选项 |
|---|------|------|
| Q1 | TaskMachine 中的 TaskMachine 类保留还是重构？ | A: 保留重构 / B: 用 StateMachine 替代 |
| Q2 | ProjectContext 是聚合视图还是实现类？ | A: 聚合视图 / B: 实现类 |
| Q3 | 是否需要支持工作流编排（如 BPMN）？ | A: v1不需要 / B: v1预留接口 |
| Q4 | LLM 适配器优先支持哪些 provider？ | A: OpenAI / B: Anthropic / C: 都支持 |

### 6.2 评审结论

```
┌─────────────────────────────────────────────────────────────────┐
│                       评审结论                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📋 文档完整性:        ✅ 通过                                    │
│  📐 架构合理性:        ✅ 通过（需小幅修正）                        │
│  🔧 技术可行性:        ✅ 通过（需补充异常体系）                     │
│  📅 计划可执行性:      ✅ 通过（需补充基础设施任务）                  │
│  🔗 一致性:           ⚠️ 需修正（4处跨文档问题）                    │
│                                                                 │
│  综合评价:            ✅ 方案可行，建议修正后执行                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、附录

### A. 评审清单

- [x] 文档覆盖完整性
- [x] 架构设计合理性
- [x] 技术选型适当性
- [x] 实施计划可行性
- [x] 跨文档一致性
- [ ] 安全性考虑（建议补充）
- [ ] 性能基准（建议补充）

### B. 评审人员

| 角色 | 姓名 | 日期 |
|------|------|------|
| 架构评审 | AI助手 | 2026-05-14 |
| 技术评审 | AI助手 | 2026-05-14 |
| 计划评审 | AI助手 | 2026-05-14 |

---

> ⚠️ **待确认**: 请确认上述问题和建议，特别是 Decision Items (Q1-Q4)
