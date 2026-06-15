# FitMind Agent Architecture

## 1. 文档目标

这份文档描述 FitMind V1 当前已实现的架构。它不是早期设计方案，而是基于实际代码的架构基线。

本版本回答三个问题：

1. FitMind 的实际执行链路是怎样的。
2. 各模块如何分工和协作。
3. 数据如何在系统中流动和落库。

---

## 2. 项目职责

FitMind V1 的核心职责是：

> 把用户与系统之间关于训练记录、饮食、身体状态和训练计划的自然语言对话，稳定地转化为结构化事实，并通过草稿确认机制安全落库。

### 2.1 V1 已支持的能力

- 记录当日训练记录（含动作明细）
- 记录当日饮食（含 ReAct 营养工具和累计估算）
- 记录当日身体状态（睡眠、疲劳、酸痛等）
- 更新长期训练计划
- 多轮草稿确认/修正/取消流程
- 普通 LLM 对话（含 session summary 上下文压缩）
- 保存完整会话、每轮消息和意图识别日志
- Token 使用统计（旁路写入）

### 2.2 V1 不承担的职责

- 自动生成高精度医学建议
- 自动生成长期训练周期
- 依赖视觉识别动作质量
- 对营养做严谨临床级计算
- 最近训练总结（已预留路由，业务模块待实现）
- 当日训练推荐（已预留路由，业务模块待实现）

---

## 3. 系统原则

### 3.1 服务链模式，不做复杂 Agent 编排

当前实现采用 `意图识别 → 路由 → 服务链依次尝试` 的确定性模式，不使用 Supervisor / Subagent 设计。

### 3.2 LLM 负责理解，代码负责约束

LLM 可以做：

- 意图识别
- 事实抽取（生成结构化 JSON）
- 草稿内容生成

代码必须做：

- schema 校验（Pydantic）
- 幂等控制
- 主键与关联关系维护
- 写入顺序控制
- 草稿状态机管理
- Token 统计

### 3.3 草稿确认机制

所有业务写入（训练、饮食、身体状态、训练计划）均经过 草稿确认流程：

```
用户输入 → LLM 提取 → 写入 draft 表 → 用户确认 → 写入正式表
```

用户可以在确认前修正或取消。

### 3.4 对话和事实同等重要

所有与 LLM 的交互都要落库，包括：

- 用户原始输入（`conversation_logs`）
- 意图识别结果（`intent_recognition_logs`）
- LLM 调用明细（`llm_call_logs`）
- 每轮 token 消耗（`chat_turn_token_usage`）

---

## 4. 架构总览

FitMind V1 的架构是一个 顺序服务链：

```text
User
  → ChatService.handle()
    → IntentClassifier (keyword rules → LLM classification)
    → IntentRouter (intent → module route)
    → [pending workflow context check]
    → NutritionRecordService.maybe_handle()
    → BodyStatusRecordService.maybe_handle()
    → WorkoutRecordService.maybe_handle()
    → WorkoutPlanService.maybe_handle()
    → fallback: general LLM chat
```

### 4.1 为什么不是 Supervisor + Subagents

初期设计曾考虑 Supervisor + Subagent 模式，但在实现中发现：

- 意图分类 + 顺序服务链已足够覆盖当前业务场景
- 每个 Service 的 `maybe_handle()` 模式天然支持"第一个匹配即处理"的优先级路由
- 草稿状态机由各 Service 内部管理，不需要跨 Agent 协调
- 避免了不必要的编排复杂度

### 4.2 为什么不是 LangGraph 为主的图编排

LangGraph 目前仅在营养记录链路中使用（`NutritionLangGraphReActRunner`），用于驱动 ReAct 循环（LLM 决策 → 工具调用 → observation 回灌）。整体请求链路不使用 LangGraph 图编排。

---

## 5. 核心组件

### 5.1 ChatService

位置：`agent/src/fitmind_agent/services/chat_service.py`

这是唯一的请求入口编排器。职责：

- 接收用户消息
- 管理 session 生命周期（创建、恢复、刷新）
- 协调意图识别和路由
- 检测 pending workflow context（是否存在待确认草稿）
- 按顺序调用各领域 Service 的 `maybe_handle()`
- 无匹配时回退到通用 LLM 对话
- 流式（SSE）和非流式两种响应模式

### 5.2 IntentClassifier

位置：`agent/src/fitmind_agent/services/intent_classifier.py`

双层意图识别：

1. **关键词规则预判**：对 6 个业务意图维护关键词表，计算命中率得出置信度
2. **LLM 分类**：调用 LLM 输出 `{"intent": "...", "confidence": ..., "reason": "..."}`

置信度决策规则：

- LLM 置信度 >= 0.7 → 采用 LLM 结果
- 否则，关键词置信度 >= 0.55 → 采用关键词结果
- 两者都不满足 → fallback 为 `unknown`

支持的意图类型（定义在 `schemas/intent.py`）：

- `today_workout_record`
- `recent_workout_summary`
- `today_workout_recommendation`
- `today_nutrition_record`
- `today_body_status_record`
- `user_workout_plan_update`
- `general_chat`
- `unknown`

### 5.3 IntentRouter

位置：`agent/src/fitmind_agent/services/intent_router.py`

将意图映射到模块路由信息（模块名、状态、数据库 intent_type、描述）。当前路由表：

| 意图 | 模块名 | 状态 |
| --- | --- | --- |
| `today_workout_record` | `workout_record_writer` | ready |
| `today_nutrition_record` | `nutrition_record_react_writer` | ready |
| `today_body_status_record` | `body_status_writer` | ready |
| `user_workout_plan_update` | `workout_plan_updater` | ready |
| `general_chat` | `general_chat` | ready |
| `recent_workout_summary` | `workout_summary_agent` | placeholder |
| `today_workout_recommendation` | `workout_recommendation_agent` | placeholder |
| `unknown` | `clarification_agent` | placeholder |

### 5.4 领域 Service（maybe_handle 模式）

每个领域 Service 实现统一的 `maybe_handle()` 接口：

```python
def maybe_handle(self, *, user_id, session_id, user_query, intent_result) -> WorkflowResult:
    # 1. 检查是否存在 pending draft → 处理确认/取消/修正
    # 2. 检查 intent_result 是否匹配本 Service → 不匹配则返回 handled=False
    # 3. LLM 提取结构化 JSON → 写入 draft → 返回确认提示
```

#### NutritionRecordService

位置：`agent/src/fitmind_agent/services/nutrition_record_service.py`

特点：
- 使用 `NutritionLangGraphReActRunner` 驱动 ReAct 循环
- LLM 可调用 `search_food_nutrition`、`estimate_food_weight`、`calculate_nutrition`、`sum_daily_nutrition` 等工具
- 营养估算字段（热量、蛋白、碳水、脂肪）为当天累计值
- draft 写入 `nutrition_record_drafts`，确认后写入 `user_nutrition_records`

#### BodyStatusRecordService

位置：`agent/src/fitmind_agent/services/body_status_record_service.py`

特点：
- 轻量 LLM 抽取（不涉及工具调用）
- 结构化字段（睡眠、疲劳、压力、酸痛、体重、情绪）保存当天最新非空快照
- draft 写入 `body_status_record_drafts`，确认后写入 `user_body_status_records`

#### WorkoutRecordService

位置：`agent/src/fitmind_agent/services/workout_record_service.py`

特点：
- LLM 从自然语言中提取训练动作、组数、重量等
- draft 写入 `workout_record_drafts`，确认后写入 `user_workout_records` + `user_workout_record_items`

#### WorkoutPlanService

位置：`agent/src/fitmind_agent/services/workout_plan_service.py`

特点：
- LLM 提取训练计划标题、日期、内容等
- draft 写入 `workout_plan_drafts`，确认后写入 `user_workout_plans`

### 5.5 Pending Workflow Context

位置：`chat_service.py` 中的 `_get_pending_workflow_context()`

当用户发来新消息时，ChatService 会检查当前 session 下是否存在待确认的草稿。如果存在：

- 若用户消息匹配确认/取消/修正/提问关键词 → 将意图覆写为草稿对应的业务意图，让对应 Service 处理
- 若用户表达新意图且与 pending 意图冲突 → 提示用户先处理当前草稿

这确保了多轮草稿对话的连贯性。

### 5.6 对话上下文与记忆

#### ConversationContextBuilder

位置：`agent/src/fitmind_agent/services/chat_context.py`

构建 LLM 对话消息列表，包含：

- 最近 N 轮对话历史（从 `conversation_logs` 加载）
- 当前 session 的已压缩 summary（从 `chat_session_summaries` 加载）
- 系统 prompt

#### SessionSummaryService

位置：`agent/src/fitmind_agent/services/session_summary_service.py`

当 session 消息数达到阈值时，异步压缩生成 summary，写入 `chat_session_summaries`。

#### MemoryService

位置：`agent/src/fitmind_agent/services/memory_service.py`

管理用户自定义记忆和 Agent 提取长期记忆的读写。

### 5.7 Token 使用追踪

位置：`agent/src/fitmind_agent/services/token_usage_tracker.py`

旁路系统，每次 LLM 调用后异步记录 token 消耗到 `llm_call_logs`，每轮对话结束后汇总到 `chat_turn_token_usage`。写入失败不影响主业务。

### 5.8 LLM 调用

#### DeepSeekLLMClient

位置：`agent/src/fitmind_agent/core/llm.py`

基于 OpenAI-compatible SDK 的 LLM 客户端，支持：

- 非流式生成（用于意图识别、结构化提取）
- 流式生成（用于普通对话回复）
- 自动提取 API 返回的 usage 信息

#### PromptLoader

位置：`agent/src/fitmind_agent/services/prompt_loader.py`

从 `prompts/` 目录加载 prompt 模板，支持变量渲染。

---

## 6. 请求执行链路

### 6.1 业务记录链路（以训练记录为例）

```text
用户消息
  → ChatService.handle()
  → resolve session_id (chat_sessions)
  → IntentClassifier.classify()  [keyword + LLM]
  → IntentRouter.route()  [intent → module route]
  → persist intent_recognition_logs
  → check pending workflow context
  → WorkoutRecordService.maybe_handle()
    → 检查 intent 是否匹配 (today_workout_record)
    → 检查是否存在 pending draft
    → LLM 提取结构化 workout JSON
    → 写入 workout_record_drafts (status=pending)
    → 返回确认提示
  → persist conversation_logs (user + assistant)
  → schedule session compression
```

### 6.2 确认链路（用户回复"确认保存"）

```text
用户消息 "确认保存"
  → ChatService.handle()
  → IntentClassifier.classify()  → general_chat (低置信度)
  → pending workflow context 检测 → 覆写意图为 today_workout_record
  → WorkoutRecordService.maybe_handle()
    → 找到 pending draft
    → 匹配确认关键词
    → 写入 user_workout_records + user_workout_record_items
    → 更新 draft status=confirmed, workout_record_id=...
  → persist conversation_logs
```

### 6.3 修正链路（用户回复修正内容）

```text
用户消息 "把卧推改成 55kg"
  → pending workflow context → 覆写意图
  → WorkoutRecordService.maybe_handle()
    → 找到 pending draft
    → 不匹配确认/取消/提问关键词 → 视为修正
    → LLM 基于 user_query + previous_draft 重新提取
    → 更新 draft (raw_text 追加, draft_payload 更新)
    → 返回新的确认提示
```

### 6.4 普通对话链路

```text
用户消息
  → IntentClassifier → general_chat (或 unknown/placeholder intent)
  → 所有 Service.maybe_handle() 返回 handled=False
  → ConversationContextBuilder.build_messages()
  → LLMService.stream()
  → persist conversation_logs
  → schedule session compression
```

---

## 7. 数据库表

当前已建表（models.py 中定义）：

| 表名 | 用途 |
| --- | --- |
| `users` | 用户主表 |
| `user_profiles` | 用户特征（身高、体重、目标等） |
| `user_workout_plans` | 训练计划 |
| `user_workout_records` | 训练记录主表 |
| `user_workout_record_items` | 训练动作明细 |
| `workout_record_drafts` | 训练记录草稿 |
| `workout_plan_drafts` | 训练计划草稿 |
| `user_nutrition_records` | 饮食记录 |
| `nutrition_record_drafts` | 饮食记录草稿 |
| `user_body_status_records` | 身体状态记录 |
| `body_status_record_drafts` | 身体状态草稿 |
| `conversation_logs` | 对话日志 |
| `intent_recognition_logs` | 意图识别日志 |
| `chat_sessions` | 会话管理 |
| `chat_session_summaries` | 会话摘要 |
| `user_defined_memories` | 用户自定义记忆 |
| `agent_derived_memories` | Agent 提取记忆 |
| `llm_call_logs` | LLM 调用明细 |
| `chat_turn_token_usage` | 每轮 token 汇总 |

---

## 8. 当前文件结构

```text
agent/src/fitmind_agent/
  api/
    app.py                    — FastAPI 应用工厂
    routes/
      chat.py                 — /api/v1/chat, /api/v1/chat/stream
      llm.py                  — /api/v1/llm/chat
      memory.py               — 记忆管理端点
      meta.py                 — /api/v1/meta, /healthz
  core/
    config.py                 — Pydantic-settings 配置
    llm.py                    — DeepSeekLLMClient (OpenAI-compatible)
  db/
    base.py                   — SQLAlchemy DeclarativeBase
    models.py                 — 全部 ORM 模型
    session.py                — 会话工厂和依赖注入
  graphs/
    [deprecated]              — 占位 LangGraph 代码，已被 intent 系统替代
  mcp/
    nutrition_server.py       — MCP 营养查询服务
  prompts/
    body_status_record_extraction/
    intent_classification/
    nutrition_react_loop/
    session_summary/
    workout_plan_update_extraction/
    workout_record_extraction/
  repositories/
    intent.py                 — intent_recognition_logs CRUD
    memory.py                 — 会话/摘要/记忆 CRUD
    nutrition.py              — 饮食记录和草稿 CRUD
    token_usage.py            — LLM 调用日志和 token 汇总 CRUD
    workout.py                — 训练记录/草稿和计划 CRUD
  schemas/
    chat.py
    intent.py                 — IntentCode, IntentRecognitionResult 等
    llm.py
    memory.py
    nutrition.py
    plan.py                   — WorkoutPlanWorkflowResult 等
    workout.py
  services/
    body_status_record_service.py
    chat_context.py           — 对话上下文构建器
    chat_service.py           — 主编排器
    intent_classifier.py      — 关键词 + LLM 意图分类
    intent_router.py          — 意图路由表
    llm_service.py            — LLM 交互封装
    memory_service.py
    nutrition_react_tools.py  — ReAct 引擎和营养工具
    nutrition_record_service.py
    prompt_loader.py
    session_summary_service.py
    token_usage_tracker.py    — Token 使用旁路统计
    workout_plan_service.py
    workout_record_service.py
```

---

## 9. 架构结论

FitMind V1 的实际架构是一个 顺序服务链，核心设计决策是：

- 用 `IntentClassifier` + `IntentRouter` 取代复杂的 Supervisor/Subagent 编排
- 用 `maybe_handle()` 模式实现领域 Service 的优先级路由
- 用草稿确认机制（draft → confirm → persist）保证写库安全
- 用 pending workflow context 保证多轮草稿对话的连贯性
- 营养链路使用 LangGraph ReAct 循环驱动工具调用
- Token 统计作为旁路系统，不影响主业务链路

所有 LLM 调用通过 `DeepSeekLLMClient` 统一，所有数据库写入通过 Repository 层统一，所有结构化数据通过 Pydantic schema 校验。
