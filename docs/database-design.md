# FitMind Database Design V3

## 1. 文档目标

这份文档定义 FitMind 当前版本的核心数据库设计。

当前版本不是只覆盖基础业务表，而是在原有用户、训练、饮食、状态、对话日志的基础上，进一步纳入记忆系统设计，使数据库能够同时支撑：

- 核心健身业务落库
- 对话日志管理
- 用户长期偏好管理
- Agent 长期记忆管理
- Session 短期记忆管理

当前版本主要回答两个问题：

1. FitMind 的核心业务数据应该如何存。
2. FitMind 的记忆系统应该如何和现有业务表衔接。

---

## 2. 设计原则

### 2.1 先做核心应用表和核心记忆表

当前版本优先落地最核心的业务表和记忆表，不做过度设计。

本次只保留以下数据主线：

- 用户
- 用户特征
- 用户训练计划
- 用户训练记录
- 用户训练动作明细
- 用户饮食记录
- 用户睡眠身体状态
- 对话历史日志
- 意图识别追踪日志
- 用户自定义长期记忆
- Agent 提取长期记忆
- Session
- Session Summary

### 2.2 原文优先，结构逐步增强

因为 FitMind 的输入来自自然语言，所以第一版要接受“很多内容先保存原文，再逐步结构化”的策略。

因此有些表在 V1 中会直接存：

- `raw_text`

这样做的好处：

- 不限制用户输入风格
- 不强迫计划必须按周拆分
- 后续可以重新解析
- 降低第一版落库难度

### 2.3 训练按“天”聚合

训练记录表以“用户某一天的一次训练记录”为核心。

设计上采用：

- 一天一条训练主记录
- 一条训练主记录下，对应多条动作明细记录

### 2.4 饮食和身体状态按“天”聚合

第一版中：

- 用户饮食：一天一条
- 用户睡眠身体状态：一天一条

这样最适合后续做日历视图、日报、周报和趋势分析。

### 2.5 保留和 Web / Agent 的对话历史

虽然当前不做复杂执行审计，但仍然要保存用户与系统的对话日志，方便：

- 回放上下文
- 纠错
- 重新解析
- 问题排查

### 2.6 记忆按层管理，不做单表混存

FitMind 的记忆系统不建议只做一张通用 `memory` 表。

更合理的方式是分成：

- 用户自定义长期记忆
- Agent 提取长期记忆
- Session 级短期记忆

这样更有利于：

- 优先级控制
- 冲突处理
- 版本更新
- prompt 召回

---

## 3. 第一版核心表清单

当前版本推荐保留以下 14 张核心表：

1. `users`
2. `user_profiles`
3. `user_workout_plans`
4. `user_workout_records`
5. `user_workout_record_items`
6. `user_nutrition_records`
7. `user_body_status_records`
8. `conversation_logs`
9. `user_defined_memories`
10. `agent_derived_memories`
11. `chat_sessions`
12. `chat_session_summaries`
13. `workout_record_drafts`
14. `intent_recognition_logs`

---

## 4. 核心关系

```text
users
  -> user_profiles
  -> user_workout_plans
  -> user_workout_records
  -> user_nutrition_records
  -> user_body_status_records
  -> conversation_logs
  -> intent_recognition_logs
  -> user_defined_memories
  -> agent_derived_memories
  -> chat_sessions

user_workout_records
  -> user_workout_record_items
  <- workout_record_drafts

chat_sessions
  -> chat_session_summaries
  -> conversation_logs
  -> intent_recognition_logs
  -> workout_record_drafts
```

---

## 5. 表设计

## 5.1 用户表

### `users`

用途：

- 存储系统用户主信息

字段建议：

- `id`
- `email`
- `username`
- `password_hash`
- `display_name`
- `avatar_url`
- `status`
- `last_login_at`
- `created_at`
- `updated_at`

约束建议：

- unique(`email`)
- unique(`username`)

说明：

- 使用普通用户表结构，不引入租户模型
- `password_hash` 只保存加密后的密码
- `status` 建议值：`active`, `disabled`, `deleted`

---

## 5.2 用户特征表

### `user_profiles`

用途：

- 存储用户的健身背景信息和个人特征

字段建议：

- `id`
- `user_id`
- `gender`
- `birth_date`
- `height_cm`
- `weight_kg`
- `target_weight_kg`
- `goal_type`
- `training_level`
- `injury_notes`
- `medical_notes`
- `diet_preference`
- `preferred_training_days`
- `remark`
- `created_at`
- `updated_at`

说明：

- `goal_type` 例如：减脂、增肌、维持、运动表现提升
- `training_level` 例如：新手、初级、中级、高级
- 这一张表是一对一附属表，一个用户对应一条主特征记录

---

## 5.3 用户训练计划表

### `user_workout_plans`

用途：

- 保存用户输入的训练计划原文

设计要求：

- 不要求强制按周拆分
- 不要求强制拆成动作结构
- 第一版只存一段用户输入文本

字段建议：

- `id`
- `user_id`
- `title`
- `plan_date`
- `raw_text`
- `source`
- `status`
- `remark`
- `created_at`
- `updated_at`

字段说明：

- `title`
  计划标题，可为空，例如“本周训练计划”或“今天练腿”
- `plan_date`
  对应计划日期，可为空
- `raw_text`
  用户输入的完整训练计划原文
- `source`
  建议值：`manual`, `agent`
- `status`
  建议值：`active`, `archived`

说明：

- 这一版的重点是先把计划文本完整保存下来
- 后续如果需要把计划拆成日计划或动作计划，可以在此基础上新增解析表

---

## 5.4 用户健身记录表

### `user_workout_records`

用途：

- 存储用户每天的训练主记录
- 一天对应一条主记录

字段建议：

- `id`
- `user_id`
- `record_date`
- `plan_id`
- `session_name`
- `duration_minutes`
- `completion_status`
- `perceived_exertion`
- `energy_level`
- `mood`
- `raw_text`
- `remark`
- `created_at`
- `updated_at`

字段说明：

- `record_date`
  训练日期，一天一条
- `plan_id`
  可关联训练计划，可为空
- `session_name`
  例如：练胸、练腿、跑步、有氧
- `completion_status`
  建议值：`completed`, `partial`, `skipped`
- `perceived_exertion`
  主观训练强度，例如 1-10
- `raw_text`
  用户当天训练过程的自然语言原文

说明：

- 这是一张训练主表
- 具体动作、组数等不直接存这里，而是放在明细表里

### `workout_record_drafts`

用途：

- 保存 Agent 从对话中提取出来、但尚未经过用户确认的训练记录结构化 JSON
- 支撑“提取 -> 用户确认/修正 -> 正式落库”的多轮流程

字段建议：

- `id`
- `user_id`
- `session_id`
- `status`
- `raw_text`
- `draft_payload`
- `confidence_score`
- `confirmed_at`
- `workout_record_id`
- `remark`
- `created_at`
- `updated_at`

字段说明：

- `draft_payload`
  保存待确认训练记录 JSON，包括日期、训练名称、动作、组数、次数、重量等
- `status`
  建议值：`pending`, `confirmed`, `cancelled`, `superseded`
- `workout_record_id`
  用户确认后，关联正式写入的 `user_workout_records.id`

说明：

- 这张表不是最终业务记录表，只是确认流程状态表
- 用户确认前不写入正式训练记录
- 用户多轮修正时更新同一条 pending draft

---

## 5.5 用户训练日志明细表

### `user_workout_record_items`

用途：

- 存储某条训练记录下的动作明细
- 一条训练主记录可以对应多条动作明细

字段建议：

- `id`
- `workout_record_id`
- `sequence_no`
- `exercise_name`
- `sets_count`
- `reps_text`
- `weight_text`
- `duration_text`
- `distance_text`
- `raw_text`
- `remark`
- `created_at`
- `updated_at`

字段说明：

- `workout_record_id`
  关联 `user_workout_records.id`
- `sequence_no`
  动作顺序
- `exercise_name`
  动作名称，例如卧推、深蹲、硬拉、跑步
- `sets_count`
  组数
- `reps_text`
  次数描述，例如 `5x5`、`12/10/8`
- `weight_text`
  重量描述，例如 `60kg`
- `duration_text`
  时长描述，例如 `30分钟`
- `distance_text`
  距离描述，例如 `5公里`
- `raw_text`
  这一条动作记录的原始文本

说明：

- 这里不强求所有动作都完全标准化
- 第一版以“可记录、可回放、可后续解析”为目标

---

## 5.6 用户饮食表

### `user_nutrition_records`

用途：

- 存储用户每日饮食记录
- 单用户一天一条
- 以 `raw_text` 保存原文

字段建议：

- `id`
- `user_id`
- `record_date`
- `raw_text`
- `calories_estimate`
- `protein_g_estimate`
- `carbs_g_estimate`
- `fat_g_estimate`
- `remark`
- `created_at`
- `updated_at`

说明：

- 第一版核心仍然是 `raw_text`
- 后面的营养估算字段可以为空
- 后续如果需要拆成早餐/午餐/晚餐明细，可再新增子表

---

## 5.7 用户睡眠身体状态表

### `user_body_status_records`

用途：

- 存储用户每日睡眠与身体状态记录
- 单用户一天一条

字段建议：

- `id`
- `user_id`
- `record_date`
- `sleep_hours`
- `fatigue_level`
- `stress_level`
- `soreness_level`
- `body_weight_kg`
- `mood`
- `raw_text`
- `remark`
- `created_at`
- `updated_at`

说明：

- 第一版允许结构化字段和原文同时存在
- 如果用户只说“今天状态一般，腿有点酸”，也可以只保存 `raw_text`

---

## 5.8 对话历史表

### `conversation_logs`

用途：

- 保存用户与 FitMind 的对话历史

字段建议：

- `id`
- `user_id`
- `thread_id`
- `session_id`
- `record_date`
- `role`
- `message_text`
- `intent_type`
- `related_plan_id`
- `related_workout_record_id`
- `related_nutrition_record_id`
- `related_body_status_record_id`
- `created_at`

字段说明：

- `thread_id`
  用于区分不同对话线程
- `session_id`
  用于标识当前消息属于哪个 session
- `role`
  建议值：`user`, `assistant`, `system`
- `intent_type`
  建议值：`plan`, `workout`, `nutrition`, `body_status`, `correction`, `query`

说明：

- 这一版只做轻量对话日志保存
- 不再引入复杂的 LLM 调用链路表
- 但会补齐 session 归属关系，支撑短期记忆系统

---

## 5.9 意图识别追踪日志表

### `intent_recognition_logs`

用途：

- 保存每一轮用户输入的意图识别结果
- 支撑后续调试、统计、回放和意图分类质量评估

字段建议：

- `id`
- `user_id`
- `thread_id`
- `session_id`
- `message_text`
- `final_intent`
- `confidence_score`
- `source`
- `reason`
- `keyword_intent`
- `keyword_confidence`
- `matched_keywords`
- `module_name`
- `module_status`
- `db_intent_type`
- `created_at`

字段说明：

- `final_intent`
  最终采用的业务意图，例如 `today_workout_record`
- `source`
  最终结果来源，建议值：`llm`, `keyword`, `fallback`
- `keyword_intent`
  关键词规则预判的候选意图，可为空
- `matched_keywords`
  关键词规则命中的词列表，使用 JSON 保存
- `module_name`
  意图路由后命中的业务模块名称
- `db_intent_type`
  映射到对话日志中的粗粒度业务类型

说明：

- 这张表属于观测日志，不替代 `conversation_logs`
- 每条用户消息最多写入一条意图识别日志
- 即使后续业务模块失败，也可以通过这张表追踪当时的分流依据

---

## 5.10 用户自定义长期记忆表

### `user_defined_memories`

用途：

- 保存用户主动要求系统记住的偏好、长期设定和限制条件

字段建议：

- `id`
- `user_id`
- `memory_key`
- `memory_category`
- `memory_value`
- `raw_text`
- `priority`
- `status`
- `source_conversation_log_id`
- `created_at`
- `updated_at`

字段说明：

- `memory_key`
  例如 `goal_type`, `response_style`, `diet_rule`
- `memory_category`
  例如 `fitness_preference`, `conversation_preference`
- `memory_value`
  建议存短文本或 JSON 字符串
- `raw_text`
  用户原始表达
- `priority`
  用户显式设定默认较高
- `status`
  建议值：`active`, `archived`

说明：

- 这一层是最高优先级长期记忆
- 如果和 Agent 推断记忆冲突，优先采用用户显式记忆

---

## 5.11 Agent 提取长期记忆表

### `agent_derived_memories`

用途：

- 保存 Agent 根据对话历史和业务记录提炼出的长期用户画像

字段建议：

- `id`
- `user_id`
- `memory_category`
- `memory_type`
- `summary_text`
- `structured_payload`
- `confidence_score`
- `source_session_id`
- `source_conversation_log_id`
- `status`
- `valid_from`
- `valid_to`
- `created_at`
- `updated_at`

字段说明：

- `memory_category`
  一级分类
- `memory_type`
  更细的记忆类型
- `summary_text`
  人类可读总结
- `structured_payload`
  JSON 结构化内容
- `confidence_score`
  提炼可信度
- `status`
  建议值：`active`, `superseded`, `expired`

说明：

- 这类记忆来自 Agent 推断，不应直接覆盖用户显式记忆
- 建议保留版本演进过程

---

## 5.12 Session 表

### `chat_sessions`

用途：

- 标识一次连续对话 session
- 管理哪些 `conversation_logs` 属于同一段短期上下文

字段建议：

- `id`
- `user_id`
- `thread_id`
- `session_no`
- `title`
- `status`
- `started_at`
- `ended_at`
- `last_message_at`
- `created_at`
- `updated_at`

字段说明：

- `thread_id`
  与 `conversation_logs.thread_id` 对齐
- `session_no`
  同一个 thread 下的顺序号
- `status`
  建议值：`active`, `closed`, `archived`

说明：

- 一个 thread 可以拆成多个 session
- 一个 session 对应多条 `conversation_logs`

---

## 5.13 Session Summary 表

### `chat_session_summaries`

用途：

- 保存单个 session 的短期摘要
- 支撑长对话压缩和长期记忆候选提炼

字段建议：

- `id`
- `session_id`
- `user_id`
- `summary_type`
- `summary_text`
- `structured_payload`
- `summary_version`
- `source_message_count`
- `created_at`
- `updated_at`

字段说明：

- `summary_type`
  建议值：`running_summary`, `final_summary`, `memory_candidate`
- `summary_text`
  直接给 Agent 使用的摘要文本
- `structured_payload`
  当前 session 的结构化要点
- `summary_version`
  支持同一 session 多次刷新摘要
- `source_message_count`
  当前摘要覆盖的消息条数

---

## 6. 推荐索引

### 用户相关

- unique(`users.email`)
- unique(`users.username`)

### 训练计划相关

- index(`user_workout_plans.user_id`, `plan_date`)

### 训练记录相关

- unique(`user_workout_records.user_id`, `record_date`)
- index(`user_workout_records.plan_id`)
- index(`user_workout_record_items.workout_record_id`, `sequence_no`)

### 饮食相关

- unique(`user_nutrition_records.user_id`, `record_date`)

### 身体状态相关

- unique(`user_body_status_records.user_id`, `record_date`)

### 对话日志相关

- index(`conversation_logs.user_id`, `record_date`)
- index(`conversation_logs.thread_id`, `created_at`)
- index(`conversation_logs.session_id`, `created_at`)

### 意图识别日志相关

- index(`intent_recognition_logs.user_id`, `created_at`)
- index(`intent_recognition_logs.session_id`, `id`)
- index(`intent_recognition_logs.final_intent`, `created_at`)

### 用户自定义记忆相关

- index(`user_defined_memories.user_id`, `memory_category`, `status`)
- index(`user_defined_memories.user_id`, `memory_key`, `status`)

### Agent 记忆相关

- index(`agent_derived_memories.user_id`, `memory_category`, `status`)
- index(`agent_derived_memories.user_id`, `memory_type`, `status`)
- index(`agent_derived_memories.source_session_id`)

### Session 相关

- unique(`chat_sessions.user_id`, `thread_id`, `session_no`)
- index(`chat_sessions.user_id`, `status`, `last_message_at`)
- index(`chat_session_summaries.session_id`, `summary_type`, `summary_version`)

---

## 7. 第一版业务落库方式

## 7.1 用户提交训练计划

用户输入：

> 这周我想练三天，周一胸肩三头，周三背二头，周五腿

V1 落库方式：

- 写入 `user_workout_plans`
- 把整段文本存入 `raw_text`

不要求：

- 立即拆成每周每日结构
- 立即拆成动作明细

## 7.2 用户记录当天训练

用户输入：

> 今天练胸，卧推 60kg 5x5，上斜哑铃推举 4 组，最后夹胸 3 组

V1 落库方式：

1. 在 `user_workout_records` 中写入一条当天训练主记录
2. 在 `user_workout_record_items` 中写入多条动作明细

## 7.3 用户记录饮食

用户输入：

> 今天早餐吃了鸡蛋燕麦，午饭吃了鸡胸米饭，晚上喝了蛋白粉

V1 落库方式：

- 在 `user_nutrition_records` 中按日期写一条记录
- 主要保存 `raw_text`

## 7.4 用户记录睡眠和状态

用户输入：

> 昨晚睡了 6 小时，今天有点疲劳，腿很酸

V1 落库方式：

- 在 `user_body_status_records` 中按日期写一条记录
- 能解析的字段可以写入结构化列
- 解析不全时至少保留 `raw_text`

## 7.5 用户设定长期偏好

用户输入：

> 以后回答简洁一点，我现在主要目标是减脂，一周练四天

落库方式：

1. 写入 `conversation_logs`
2. 抽取显式偏好
3. 写入 `user_defined_memories`

## 7.6 Agent 提炼长期画像

触发场景：

- session 结束
- 周期性复盘
- 多日数据总结

落库方式：

1. 读取 session summary + 历史训练 / 饮食 / 状态记录
2. 生成长期记忆候选
3. 写入 `agent_derived_memories`
4. 旧版本记忆标记为 `superseded`

## 7.7 管理短期会话记忆

落库方式：

1. 新会话开始时创建 `chat_sessions`
2. 每条消息写入 `conversation_logs`，并挂 `session_id`
3. 达到阈值或会话结束时写入 `chat_session_summaries`

---

## 8. MVP 最小落地表

如果现在就开始实现，建议第一批 migration 只建以下表：

1. `users`
2. `user_profiles`
3. `user_workout_plans`
4. `user_workout_records`
5. `user_workout_record_items`
6. `user_nutrition_records`
7. `user_body_status_records`
8. `conversation_logs`
9. `user_defined_memories`
10. `agent_derived_memories`
11. `chat_sessions`
12. `chat_session_summaries`

---

## 9. 当前版本的特点

这一版相对之前数据库设计有四个明确变化：

1. 不再以复杂的 Agent 审计表为中心。
2. 不再强制把训练计划拆成周计划或动作计划。
3. 先通过 `raw_text + 少量结构化字段` 的方式快速落地。
4. 正式引入三层记忆体系，而不是只保存对话原文。

这样更适合 FitMind 第一版产品。

---

## 10. 后续扩展方向

等这一版跑通后，再逐步新增：

1. `exercise_dictionary`
   动作标准库
2. `nutrition_items`
   饮食明细子表
3. `change_logs`
   修改历史表
4. `agent_runs`
   Agent 执行记录
5. `plan_parsed_items`
   从训练计划原文中拆出的结构化动作项
6. `memory_jobs`
   记忆提炼任务表
7. `memory_conflicts`
   记忆冲突与人工确认表

当前阶段不建议一起做进 MVP。
