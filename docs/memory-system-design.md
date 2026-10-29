# FitMind Memory System Design V1

## 1. 文档目标

这份文档用于定义 FitMind 的记忆管理系统。

设计目标不是做一个泛化的聊天记忆池，而是围绕健身助手场景，构建一套可落库、可更新、可解释的记忆系统，让 Agent 能长期理解用户、短期保持上下文，并且区分：

1. 用户自己明确设定的记忆
2. Agent 从历史对话和业务数据中提炼出的长期记忆
3. 当前会话的短期记忆

本设计参考类似 Claude Code 一类长对话 Agent 的思路，但会更贴近 FitMind 的实际业务。

---

## 2. 记忆系统总览

FitMind 的记忆建议拆成三层：

1. `用户自定义长期记忆`
2. `Agent 提取长期记忆`
3. `Session 级短期记忆`

对应推荐表如下：

1. `user_defined_memories`
2. `agent_derived_memories`
3. `chat_sessions`
4. `chat_session_summaries`

关系可以理解为：

```text
users
  -> user_defined_memories
  -> agent_derived_memories
  -> chat_sessions

chat_sessions
  -> chat_session_summaries
  -> conversation_logs
```

同时建议在现有 `conversation_logs` 上新增：

- `session_id`

这样当前对话日志就能和短期记忆系统直接关联。

---

## 3. 设计原则

### 3.1 用户明确设定优先级最高

如果用户主动说：

- 以后回答简洁一点
- 我当前主要目标是减脂
- 我一周训练四天

这类信息应优先于 Agent 自己的推断。

### 3.2 记忆必须可分类

Agent 自动提取的记忆不能只是一段自由文本，必须至少有：

- 一级分类
- 具体类型
- 文本总结
- 可选结构化结果

这样后续才方便：

- prompt 召回
- 冲突检测
- 自动更新
- 业务联动

### 3.3 短期记忆只服务当前 session

短期记忆不承担长期画像职责，它的作用是：

- 压缩上下文
- 保持当前会话连续性
- 在长对话中替代全量历史消息

### 3.4 记忆尽量可追溯

无论是用户定义记忆，还是 Agent 提炼记忆，都建议保留来源信息，例如：

- 来源消息 ID
- 来源 session ID
- 来源时间

这样后续更容易解释：

- 为什么 Agent 记住了这件事
- 这条记忆是用户说的，还是 Agent 推断的

### 3.5 记忆是可演化事实

很多记忆不是永久不变的，例如：

- 健身目标会变化
- 对话风格偏好会变化
- 当前身体状态会变化

所以记忆系统必须支持：

- 覆盖
- 失效
- 版本迭代

---

## 4. 用户自定义长期记忆

### `user_defined_memories`

用途：

- 保存用户主动要求系统记住的偏好、设定、禁忌和长期约束

这一层是最高优先级长期记忆。

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
  具体键，例如：`goal_type`, `response_style`, `diet_rule`
- `memory_category`
  一级分类
- `memory_value`
  建议保存短文本或 JSON 字符串
- `raw_text`
  用户原始表达
- `priority`
  用于冲突排序，用户主动设定通常较高
- `status`
  建议值：`active`, `archived`

### 推荐分类

#### 4.1 `fitness_preference`

健身相关偏好，例如：

- 长期目标是减脂 / 增肌 / 维持
- 一周训练几天
- 偏好力量训练还是有氧
- 偏好早晨训练还是晚上训练

#### 4.2 `content_preference`

内容呈现偏好，例如：

- 更喜欢短结论
- 更喜欢列表
- 更喜欢按训练 / 饮食 / 状态分块说明

#### 4.3 `conversation_preference`

对话风格偏好，例如：

- 回答简洁
- 少鼓励，多结论
- 一次只问一个问题

#### 4.4 `diet_preference`

饮食偏好或饮食约束，例如：

- 高蛋白优先
- 控碳
- 乳糖不耐受
- 偏好中式饮食

#### 4.5 `health_constraint_preference`

身体限制或长期注意事项，例如：

- 膝盖旧伤
- 腰部容易不适
- 不做冲击性动作

---

## 5. Agent 提取长期记忆

### `agent_derived_memories`

用途：

- 保存 Agent 根据用户历史对话、训练记录、饮食记录、身体状态记录总结出来的长期记忆

这类记忆不是用户直接写下来的，而是 Agent 归纳得到的。

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
  更细的类型标识
- `summary_text`
  面向人类可读的总结
- `structured_payload`
  JSON 结构化结果，方便下游逻辑使用
- `confidence_score`
  可信度
- `status`
  建议值：`active`, `superseded`, `expired`

---

## 6. Agent 提取记忆的推荐分类

这一部分是核心设计重点。

Agent 自动提取的长期记忆，建议至少拆成以下 8 类。

### 6.1 `fitness_goal_memory`

含义：

- 用户的长期健身目标和阶段目标

示例：

- 当前主要目标是减脂
- 更关注恢复训练习惯，而不是提升极限重量
- 近期目标是重新建立每周 4 练

来源：

- 训练计划
- 多次目标表述
- 饮食与状态变化

### 6.2 `training_pattern_memory`

含义：

- 用户稳定的训练习惯和训练模式

示例：

- 常做胸背腿三分化
- 一周通常训练 3 到 4 天
- 训练时间多在工作日晚上

来源：

- `user_workout_plans`
- `user_workout_records`
- 多个 session 的重复表达

### 6.3 `exercise_preference_memory`

含义：

- 用户偏好的动作、常做动作、回避动作和动作限制

示例：

- 喜欢卧推、深蹲、硬拉
- 不喜欢长时间跑步机
- 因膝盖不适回避跳跃动作

来源：

- `user_workout_record_items`
- 对话纠错
- 用户主观反馈

### 6.4 `body_status_baseline_memory`

含义：

- 用户长期身体状态基线和稳定风险点

示例：

- 睡眠通常偏少
- 腿部训练后恢复较慢
- 下背部是高风险疲劳区域

来源：

- `user_body_status_records`
- 状态类对话

说明：

- 这一类是长期基线，不是某一天的即时状态

### 6.5 `nutrition_pattern_memory`

含义：

- 用户长期饮食结构和营养行为模式

示例：

- 高蛋白意识较强
- 晚餐碳水偏高
- 经常忘记补充早餐蛋白

来源：

- `user_nutrition_records`
- 饮食相关对话

### 6.6 `conversation_style_memory`

含义：

- Agent 归纳出来的对话风格偏好

示例：

- 用户更喜欢直接结论
- 不喜欢冗长背景
- 更愿意接受清晰下一步建议

来源：

- 长期交互风格
- 用户反馈

说明：

- 若用户主动设定风格，用户自定义记忆优先

### 6.7 `current_phase_memory`

含义：

- 用户当前阶段性状态，是近一段时间的中期背景记忆

示例：

- 最近处于恢复训练阶段
- 最近工作忙，训练频率下降
- 最近在重新控制饮食

来源：

- 最近 7 到 30 天的综合记录

说明：

- 它不是某日即时状态，而是最近阶段的背景描述

### 6.8 `adherence_risk_memory`

含义：

- 用户执行计划时的稳定偏差和风险点

示例：

- 容易周末中断训练
- 饮食记录持续性较弱
- 工作忙时更容易放弃有氧

来源：

- 计划与实际训练偏差
- 连续日志完成度
- 多轮复盘对话

说明：

- 这一类很适合用于 Agent 的提醒与建议策略

---

## 7. 短期记忆系统

短期记忆用于管理单个会话周期内的上下文。

建议拆成两张表：

1. `chat_sessions`
2. `chat_session_summaries`

---

## 8. Session 表设计

### `chat_sessions`

用途：

- 标记一次连续对话会话
- 界定哪些 `conversation_logs` 属于当前 session

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
  同一个 thread 下第几个 session
- `status`
  建议值：`active`, `closed`, `archived`

建议规则：

- 一个用户可以有多个 thread
- 一个 thread 可以拆成多个 session
- 一个 session 对应多条 `conversation_logs`

---

## 9. Session Summary 表设计

### `chat_session_summaries`

用途：

- 保存一个 session 的短期摘要
- 用于长对话压缩
- 用于后续生成长期记忆候选

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
  可直接用于 prompt 的会话摘要
- `structured_payload`
  当前 session 的结构化要点
- `summary_version`
  支持同一 session 多次摘要迭代
- `source_message_count`
  当前摘要覆盖了多少条消息

---

## 10. 与 conversation_logs 的关系

当前系统已经有：

- `conversation_logs`

为了支持短期记忆，建议在这张表上新增：

- `session_id`

推荐关系：

```text
chat_sessions.id
  -> conversation_logs.session_id
```

这样带来的好处：

- 查询某个 session 的消息更简单
- 生成 summary 更简单
- 调试 Agent 上下文更直接

V1 不建议再额外做消息映射表，直接在 `conversation_logs` 中挂 `session_id` 就够用了。

---

## 11. 记忆写入流程建议

### 11.1 用户自定义记忆写入

触发场景：

- 用户明确说“记住这个”
- 用户主动表达稳定偏好

流程建议：

1. 识别是否为显式记忆指令
2. 提取 `memory_category`、`memory_key`、`memory_value`
3. 保存到 `user_defined_memories`
4. 记录来源 `source_conversation_log_id`

### 11.2 Agent 提取长期记忆写入

触发场景：

- session 结束时
- 多日数据汇总时
- 周期性后台提炼任务

流程建议：

1. 基于最近 session summary 和业务记录生成候选记忆
2. 为每条记忆赋予分类和可信度
3. 判断是否与已有活跃记忆冲突
4. 新增新版本，旧版本置为 `superseded`

### 11.3 Session Summary 写入

触发场景：

- 单个 session 消息条数达到阈值
- session 关闭

流程建议：

1. 拉取当前 `session_id` 下消息
2. 生成 `running_summary` 或 `final_summary`
3. 写入 `chat_session_summaries`
4. 后续读取优先使用最新版本摘要

---

## 12. 记忆读取优先级

给 Agent 组装 prompt 时，建议按以下优先级读取：

1. 当前 session 的最新 summary
2. 当前 session 最近消息
3. 用户自定义长期记忆
4. Agent 提取长期记忆
5. 原始业务记录和历史对话

可以概括成：

```text
短期上下文 > 用户显式偏好 > Agent 长期画像 > 原始历史数据
```

---

## 13. 更新策略

### 13.1 用户自定义记忆

建议策略：

- 同一 `memory_key` 的新值覆盖旧值
- 旧值标记为 `archived`

### 13.2 Agent 提取长期记忆

建议策略：

- 不直接覆盖
- 用新增版本替代旧版本
- 旧版本改为 `superseded`

### 13.3 Session Summary

建议策略：

- 允许同一 session 多次生成摘要
- 用 `summary_version` 控制版本

---

## 14. V1 最小实现建议

如果当前只落第一版，建议最少做以下内容：

1. 新增 `user_defined_memories`
2. 新增 `agent_derived_memories`
3. 新增 `chat_sessions`
4. 新增 `chat_session_summaries`
5. 为 `conversation_logs` 增加 `session_id`

这样就已经能支撑：

- 用户显式偏好记忆
- Agent 长期用户画像
- 单次会话摘要
- 长对话上下文压缩
- 记忆与对话日志关联

---

## 15. 总结

FitMind 的记忆系统不应该只有一个通用 `memory` 表。

更合理的设计是拆成三层：

- 用户自己定义的长期记忆
- Agent 自动提取的长期记忆
- Session 级短期记忆

其中，Agent 自动提取的记忆建议至少覆盖：

1. 健身目标记忆
2. 训练模式记忆
3. 动作偏好记忆
4. 身体状态基线记忆
5. 饮食模式记忆
6. 对话风格记忆
7. 当前阶段记忆
8. 执行风险记忆

这样设计后，FitMind 才能在后续逐步具备真正的长期个性化能力，而不只是单轮问答。
