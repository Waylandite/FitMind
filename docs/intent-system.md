# FitMind 意图识别系统

## 1. 文档目标

本文档记录 FitMind 当前支持的用户意图类型、识别流程、路由模块和实现状态。

意图识别系统的目标是：在用户输入进入对话流程后，先判断这句话属于哪类健身业务，再把请求分发给对应模块处理。

---

## 2. 当前识别链路

当前意图识别链路位于：

- `agent/src/fitmind_agent/services/intent_classifier.py`
- `agent/src/fitmind_agent/services/intent_router.py`
- `agent/src/fitmind_agent/services/chat_service.py`

整体流程：

1. 用户消息进入 `ChatService`
2. 系统先确保当前 `session_id`
3. 调用 `IntentClassifier.classify`
4. 先进行关键词规则预判
5. 再调用 LLM 输出结构化意图 JSON
6. 根据置信度选择最终意图
7. 通过 `IntentRouter` 映射到业务模块
8. 将意图识别结果写入 `intent_recognition_logs`
9. 根据模块状态执行真实业务逻辑或回退到普通对话

当前置信度规则：

- LLM 置信度大于等于 `0.7` 时，优先采用 LLM 结果
- 否则，如果关键词规则置信度大于等于 `0.55`，采用关键词结果
- 如果两者都不稳定，进入 `fallback`

---

## 3. Prompt 位置

意图识别 Prompt 统一存放在：

```text
agent/src/fitmind_agent/prompts/intent_classification/
```

当前包含：

- `system.txt`
- `user.txt`

LLM 被要求只输出 JSON，例如：

```json
{
  "intent": "today_workout_record",
  "confidence": 0.86,
  "reason": "用户描述了今天已经完成的训练动作和组数"
}
```

---

## 4. 支持的意图类型和实现状态

| 意图 | 中文含义 | 路由模块 | 数据类型 | 状态 | 当前能力 |
| --- | --- | --- | --- | --- | --- |
| `today_workout_record` | 当日训练记录 | `workout_record_writer` | `workout` | `ready` | 已支持训练数据提取、草稿确认、多轮修正、确认后写入训练记录表 |
| `recent_health_summary` | 最近健康情况总结 | `workout_summary_agent` | `query` | `ready` | 已接入最近 7 天训练、饮食、身体状态和长期计划的并发查询与总结 |
| `today_workout_recommendation` | 当日训练计划推荐 | `workout_recommendation_agent` | `plan` | `ready` | 已接入最新长期计划和最近 7 天训练记录的并发查询与今日训练建议生成 |
| `today_nutrition_record` | 当日饮食记录 | `nutrition_record_react_writer` | `nutrition` | `ready` | 已支持 LangGraph ReAct 营养 loop、今日上下文填充、草稿确认和饮食表落库 |
| `today_body_status_record` | 当日睡眠和身体状态记录 | `body_status_writer` | `body_status` | `ready` | 已支持睡眠、疲劳、酸痛、体重、情绪等解析和身体状态表落库 |
| `user_workout_plan_update` | 用户健身计划更新 | `workout_plan_updater` | `plan` | `ready` | 已接入长期训练计划提取、草稿确认和增量入库模块 |
| `general_chat` | 普通对话 | `general_chat` | `query` | `ready` | 已支持普通 LLM 对话、多轮上下文、session summary 上下文 |
| `unknown` | 未知或信息不足 | `clarification_agent` | `query` | `placeholder` | 仅完成意图识别和路由，澄清追问模块待实现 |

---

## 5. 已落地功能说明

### 5.1 当日训练记录

当最终意图是 `today_workout_record` 时，系统会进入训练记录工作流：

1. 调用训练记录提取 Prompt
2. 从用户自然语言中提取结构化训练 JSON
3. 创建 `workout_record_drafts` 草稿
4. 邀请用户确认
5. 支持用户继续修正或取消
6. 用户确认后写入：
   - `user_workout_records`
   - `user_workout_record_items`

相关文件：

- `agent/src/fitmind_agent/services/workout_record_service.py`
- `agent/src/fitmind_agent/repositories/workout.py`
- `agent/src/fitmind_agent/prompts/workout_record_extraction/`

### 5.2 当日饮食记录

当最终意图是 `today_nutrition_record` 时，系统会进入饮食记录工作流：

1. 读取数据库中当天已有的饮食记录，作为 LLM 上下文
2. 启动 `NutritionLangGraphReActRunner`
3. LLM 在 `llm_decide` 节点自主选择工具或输出最终 JSON
4. `tool_execute` 节点通过 MCP-ready provider 执行营养工具并回写 observation
5. 自动填充 `record_date`
6. 创建 `nutrition_record_drafts` 草稿，等待用户确认
7. 用户确认后才写入正式饮食表
8. 如果当天已有记录，新输入会追加到 `raw_text`，并保留写入时间
9. 饮食估算字段表示“今天截至目前”的累计值，由 ReAct loop 结合已有上下文重新分析后非空覆盖
10. 后续可以继续接入外部 MCP 食物营养查询、份量估算和营养汇总工具

相关文件：

- `agent/src/fitmind_agent/services/nutrition_record_service.py`
- `agent/src/fitmind_agent/services/nutrition_react_tools.py`
- `agent/src/fitmind_agent/repositories/nutrition.py`
- `agent/src/fitmind_agent/prompts/nutrition_react_loop/`

### 5.3 当日睡眠和身体状态记录

当最终意图是 `today_body_status_record` 时，系统会进入身体状态记录工作流：

1. 读取数据库中当天已有的身体状态记录，作为 LLM 上下文
2. 调用身体状态抽取 Prompt
3. 自动填充 `record_date`
4. 将睡眠、疲劳、压力、酸痛、体重、情绪等写入 `user_body_status_records`
5. 如果当天已有记录，新输入会追加到 `raw_text`，并保留写入时间
6. 身体状态结构化字段保留最新非空快照，方便快速查询当天最后状态
7. 身体状态不设计工具调用，保持轻量解析和快速落库

相关文件：

- `agent/src/fitmind_agent/services/body_status_record_service.py`
- `agent/src/fitmind_agent/repositories/nutrition.py`
- `agent/src/fitmind_agent/prompts/body_status_record_extraction/`

### 5.4 用户长期训练计划更新

当最终意图是 `user_workout_plan_update` 时，系统会进入训练计划更新工作流：

1. 调用训练计划提取 Prompt
2. 从用户自然语言中提取计划标题、日期、内容和备注
3. 创建 `workout_plan_drafts` 草稿
4. 邀请用户确认
5. 支持用户继续修正或取消
6. 用户确认后写入 `user_workout_plans`

相关文件：

- `agent/src/fitmind_agent/services/workout_plan_service.py`
- `agent/src/fitmind_agent/repositories/workout.py`
- `agent/src/fitmind_agent/prompts/workout_plan_update_extraction/`

### 5.5 最近健康情况总结

当最终意图是 `recent_health_summary` 时，系统会进入健康总结工作流：

1. 通过 `ThreadPoolExecutor(5)` 并发查询最近 7 天的训练记录、饮食记录、身体状态记录和长期训练计划
2. 各数据源查询完成后通过 SSE progress 事件实时反馈进度
3. 汇总所有数据后调用 LLM 生成结构化健康总结
4. 直接返回结果，不经过草稿确认

相关文件：

- `agent/src/fitmind_agent/services/recent_health_summary_service.py`
- `agent/src/fitmind_agent/repositories/workout.py`
- `agent/src/fitmind_agent/repositories/nutrition.py`
- `agent/src/fitmind_agent/prompts/recent_health_summary/`

### 5.6 当日训练计划推荐

当最终意图是 `today_workout_recommendation` 时，系统会进入训练推荐工作流：

1. 通过 `ThreadPoolExecutor(2)` 并发查询最新长期训练计划和最近 7 天训练记录
2. 各数据源查询完成后通过 SSE progress 事件实时反馈进度
3. LLM 结合训练历史恢复状态和长期计划生成当日训练建议
4. 直接返回结果，不经过草稿确认

相关文件：

- `agent/src/fitmind_agent/services/today_workout_recommendation_service.py`
- `agent/src/fitmind_agent/repositories/workout.py`
- `agent/src/fitmind_agent/prompts/today_workout_recommendation/`

### 5.7 普通对话

当最终意图是 `general_chat`，或业务模块尚未接入时，当前系统会进入普通 LLM 对话流程。

普通对话会加载：

- 当前 session 最近对话
- 当前 session 已压缩 summary
- 用户本轮输入

相关文件：

- `agent/src/fitmind_agent/services/chat_context.py`
- `agent/src/fitmind_agent/services/chat_service.py`
- `agent/src/fitmind_agent/services/session_summary_service.py`

---

## 6. 意图识别结果落库

当前每轮用户输入完成意图识别后，会写入 `intent_recognition_logs` 表。

主要字段：

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

用途：

- 调试意图识别质量
- 回放某次对话为什么进入某个模块
- 统计不同意图的使用频率
- 后续训练或优化分类 Prompt

查询示例：

```sql
select
  id,
  user_id,
  session_id,
  final_intent,
  confidence_score,
  source,
  module_name,
  created_at
from intent_recognition_logs
order by id desc
limit 20;
```

---

## 7. 后续扩展建议

当前 6 个业务意图中 4 个已完整实现，仅剩 `unknown` 对应的澄清追问模块。推荐在数据积累更多后继续优化：

1. `unknown` 澄清追问 — 当置信度不足时主动追问用户，缩小意图范围
2. 意图识别精度优化 — 利用 `intent_recognition_logs` 中的错误分类做 prompt 迭代
3. 健康总结和训练推荐的 LLM 质量迭代 — 收集真实用户反馈优化 prompt
