# FitMind Project Overview

> 本文档是原始长版 README 的项目说明备份，用于保留早期需求分析、架构背景和能力定义。

# FitMind

FitMind 是一个基于 Python + LangGraph 的健身智能体项目。它的目标不是“陪聊式健身助手”，而是把用户在自然语言中表达的训练计划、实际完成情况、身体状态和饮食信息，稳定地解析、结构化、校验，并最终写入数据库，形成可追踪、可分析、可回顾的个人健身数据系统。

这个项目的核心问题不是“如何回答用户”，而是“如何把模糊、口语化、多轮补充的健身表达，转成可靠的结构化事实”。

---

## 1. 需求分析

### 1.1 用户会怎么说

在真实场景中，用户不会按表单填写训练数据，而会直接说自然语言，例如：

- `今天练胸，卧推 60kg 5x5，再做上斜哑铃推举和夹胸。`
- `本来计划跑 8 公里，最后只跑了 5 公里，状态一般，后两公里掉速很厉害。`
- `今天睡得不好，腿有点酸，训练轻一点。`
- `晚饭吃了鸡胸肉、米饭和一杯蛋白粉。`
- `把刚才的卧推改成 55kg，不是 60kg。`
- `帮我看看这周是不是腿练少了。`

这意味着系统必须处理：

- 非结构化输入
- 多意图混合输入
- 多轮补充与纠错
- 计划与实际结果分离
- 训练、恢复、饮食之间的上下文关联
- 落库前的歧义消解与字段补全

### 1.2 FitMind 要解决的核心任务

FitMind 第一阶段聚焦四类核心信息：

1. `训练计划`
   用户今天准备练什么，计划做哪些动作、组数、次数、重量、时长、配速等。
2. `训练结果`
   用户最终实际完成了什么，是否完成计划，是否中途调整，强度如何。
3. `身体状态`
   睡眠、疲劳、酸痛、精神状态、受伤风险、恢复情况。
4. `饮食记录`
   餐次、食物、估算营养、补剂、进食时间。

系统最终要把这些信息沉淀为：

- 今日训练日志
- 今日饮食日志
- 今日状态日志
- 计划与实际偏差
- 可供后续周报、建议、复盘使用的结构化数据

### 1.3 第一阶段不做什么

为了控制复杂度，MVP 暂不追求：

- 自动生成高度个性化周期训练计划
- 医疗诊断
- 严格到克级别的营养估算
- 视觉识别动作质量
- 可穿戴设备深度联动

---

## 2. 项目定位

FitMind 本质上是一个“健身数据操作系统”上的对话式 Agent 层。

它做三件事：

1. `理解`
   理解用户当前在表达计划、结果、状态、饮食、纠错，还是查询分析。
2. `结构化`
   把自然语言拆成标准实体、标准动作、标准指标和标准事件。
3. `执行`
   在必要时确认歧义，然后安全地写入数据库，并返回总结、追问或建议。

一句话概括：

> FitMind = 对话式健身记录入口 + LangGraph 状态编排 + 结构化事实落库引擎

---

## 3. 为什么用 LangGraph

这个需求并不适合单次 prompt，也不适合一个“全能 Agent”直接自由调用数据库。原因有三个：

1. `这是一个强状态任务`
   用户会在多轮会话里补充、修改、纠错，系统需要维护“今天的上下文”和“当前待确认事实”。
2. `这是一个强约束任务`
   数据库写入必须可校验、可追踪、可回滚，不能让模型直接自由生成 SQL。
3. `这是一个混合任务`
   一部分步骤适合 LLM 推理，一部分步骤必须由确定性逻辑完成，比如 schema 校验、单位归一、字段补全策略、幂等写入。

LangGraph 非常适合这个场景，因为它支持：

- `StateGraph` 管理多轮状态
- `Command` 驱动节点流转
- `interrupt` 在歧义或高风险写入前请求用户确认
- `checkpoint` 保存会话执行状态
- 子图或子 Agent 组合确定性流程与 Agent 能力

参考资料：

- [LangChain Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent/index)
- [LangChain Handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)
- [LangChain Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)
- [LangGraph Human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/human-in-the-loop)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)

---

## 4. 主流 Agent 设计调研结论

### 4.1 主流模式

结合 LangChain/LangGraph 官方文档和 Anthropic 对生产级 Agent 的总结，当前主流模式可以粗分为五类：

1. `单 Agent + 工具`
   简单、成本低，适合能力边界明确的任务。
2. `Supervisor + Subagents`
   主 Agent 负责任务分发，子 Agent 专注单域问题，适合多能力协作。
3. `Handoffs`
   Agent 之间通过状态切换接管对话，适合“谁在和用户说话”会变化的场景。
4. `Router`
   先做意图分类，再把任务送到一个或多个专门处理器。
5. `Custom Workflow`
   用图把固定步骤和 Agent 步骤组合起来，最适合需要确定性控制、审计和落库的系统。

### 4.2 对 FitMind 的启发

FitMind 的任务不是纯问答，而是“自然语言 -> 事实提取 -> 校验 -> 持久化 -> 回执”。因此：

- 纯 `单 Agent + 工具` 太脆，容易把分类、抽取、纠错、落库耦合在一起。
- 纯 `handoff` 不够经济，因为这个场景里用户主要是对一个统一助手说话，不需要频繁“角色切换”。
- 纯 `router` 不够，因为很多输入是复合意图，例如一段话同时包含计划、状态和饮食。
- 最合适的是 `Custom Workflow + Subagents` 的混合模式。

### 4.3 最终推荐架构

FitMind 推荐采用：

`入口 Supervisor Agent + 多领域 Extraction Subagents + 确定性 Persistence Workflow`

设计原则：

- `Agent 负责理解和提取`
- `代码负责校验和写库`
- `图负责状态和流程`
- `用户负责确认歧义`

这也是最符合官方建议的落地方式：先选最简单的可控架构，在必要处引入 Agent，而不是让所有步骤都“自主决策”。

---

## 5. FitMind 核心能力定义

### 5.1 对话能力

- 识别训练计划
- 识别训练结果
- 识别身体状态
- 识别饮食摄入
- 识别纠错与修改
- 识别查询与复盘请求

### 5.2 结构化能力

- 动作标准化
- 重量、次数、组数、距离、时长、配速、RPE 标准化
- 时间标准化
- 食物实体标准化
- 身体状态标签化
- 同一条消息中的多事件拆分

### 5.3 数据能力

- 写入今日计划
- 写入今日实际训练
- 写入今日状态
- 写入今日饮食
- 更新已记录项目
- 生成训练偏差记录
- 生成可查询的日/周/月聚合数据

### 5.4 交互能力

- 信息不足时追问
- 高歧义时请求确认
- 落库后返回总结
- 支持用户纠正之前记录

---

## 6. 当前架构

FitMind V1 的实际架构已演变为 **顺序服务链** 模式，详见 [agent-architecture.md](agent-architecture.md)。

核心流程：

```
用户消息 → IntentClassifier (关键词 + LLM) → IntentRouter (路由) →
  ServiceChain (NutritionRecordService → BodyStatusRecordService →
  WorkoutRecordService → WorkoutPlanService) → fallback 对话
```

设计要点：

- 用 `IntentClassifier` + `IntentRouter` 取代 Supervisor/Subagent 编排
- 用 `maybe_handle()` 模式实现领域 Service 的优先级路由
- 所有业务写入经过 **草稿确认机制**（extract → draft → confirm → persist）
- 营养链路使用 LangGraph ReAct 循环驱动工具调用

### 6.1 已实现的领域 Service

| Service | 意图 | 能力 |
| --- | --- | --- |
| `WorkoutRecordService` | `today_workout_record` | 训练记录提取、草稿确认、动作明细落库 |
| `RecentHealthSummaryService` | `recent_health_summary` | 最近 7 天训练、饮食、身体状态和长期计划并发查询与总结 |
| `NutritionRecordService` | `today_nutrition_record` | 饮食记录 ReAct 提取、营养工具调用、累计估算 |
| `BodyStatusRecordService` | `today_body_status_record` | 睡眠/疲劳/酸痛/体重/情绪解析 |
| `WorkoutPlanService` | `user_workout_plan_update` | 长期训练计划提取和更新 |

### 6.2 待实现的模块

- `today_workout_recommendation` — 已预留路由，业务逻辑待实现
- `unknown` 澄清追问 — 已预留路由，业务逻辑待实现
