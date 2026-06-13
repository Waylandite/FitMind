# 意图识别与分流联调测试报告

测试日期：2026-06-13

## 目标

在用户对话进入主聊天流程后，先执行意图识别，再根据意图和置信度分流到对应业务模块。

当前模块只保留路由占位，不直接执行训练、饮食、睡眠或计划的真实落库逻辑。

## 本次实现

新增后端能力：

- 关键词规则预判：先通过硬编码关键词给出候选意图。
- LLM 意图识别：使用默认 `deepseek-v4-flash` 输出结构化 JSON。
- 置信度决策：LLM 置信度足够时采用模型结果；否则回退到关键词结果；仍不足时进入 `unknown`。
- 模块路由占位：每个意图映射到一个未来业务模块名和数据库兼容 `intent_type`。
- SSE 事件：`/api/v1/chat/stream` 会先返回 `intent` 事件，再返回模型流式内容。

新增前端能力：

- 聊天状态栏接收并展示当前意图和置信度。
- 原有流式回复和会话日志写入流程保持可用。

## 意图枚举

| intent | 含义 | 预留模块 |
| --- | --- | --- |
| `today_workout_record` | 当日健身计划或训练记录落库 | `workout_record_writer` |
| `recent_workout_summary` | 最近健身情况总结 | `workout_summary_agent` |
| `today_workout_recommendation` | 当日健身计划推荐 | `workout_recommendation_agent` |
| `today_nutrition_sleep_record` | 当日饮食、睡眠、身体状态记录 | `nutrition_body_status_writer` |
| `user_workout_plan_update` | 用户健身计划更新 | `workout_plan_updater` |
| `general_chat` | 普通对话 | `general_chat` |
| `unknown` | 无法稳定判断 | `clarification_agent` |

## 后端 API 测试

接口：

```http
POST /api/v1/chat
```

测试结果：

| Query | 识别结果 | 置信度 | 来源 | 模块 |
| --- | --- | --- | --- | --- |
| 今天练胸，卧推 5 组，飞鸟 4 组，状态不错。 | `today_workout_record` | 0.85 | `llm` | `workout_record_writer` |
| 帮我总结一下最近三天的健身情况。 | `recent_workout_summary` | 0.72 | `llm` | `workout_summary_agent` |
| 我今天不知道练什么，帮我推荐一个训练计划。 | `today_workout_recommendation` | 0.92 | `llm` | `workout_recommendation_agent` |
| 今天吃了牛肉米饭，睡了 6 小时，有点疲劳。 | `today_nutrition_sleep_record` | 0.84 | `llm` | `nutrition_body_status_writer` |
| 帮我把接下来四周的增肌计划调整一下。 | `user_workout_plan_update` | 0.88 | `llm` | `workout_plan_updater` |

结论：五类核心意图均能稳定识别，并返回对应模块占位信息。

## SSE 流式测试

接口：

```http
POST /api/v1/chat/stream
```

测试 Query：

```text
今天吃了鸡胸肉和米饭，睡眠 7 小时，肩膀有点酸。
```

首个 SSE 事件：

```json
{
  "type": "intent",
  "intent": "today_nutrition_sleep_record",
  "confidence": 0.85,
  "source": "llm",
  "module": {
    "name": "nutrition_body_status_writer",
    "status": "placeholder"
  }
}
```

随后正常返回 `delta` 流式内容。

结论：流式接口已满足“先识别意图，再进入回答生成”的链路要求。

## 前后端联调

前端页面：

```text
http://127.0.0.1:5173/
```

测试 Query：

```text
今天吃了鸡胸肉和米饭，睡了 7 小时，肩膀有点酸。
```

联调结果：

- 前端状态栏展示：`已完成 · today_nutrition_sleep_record · 85%`
- 模型回复正常流式渲染。
- 当前会话列表正常刷新。
- `conversation_logs` 写入成功。
- 用户日志和助手日志的数据库兼容 `intent_type` 均为 `nutrition`。

## 测试结论

本轮意图识别、置信度输出、模块占位分流、SSE 事件、前端展示和日志写入均已联调通过。

下一步可以在 `IntentRouter` 对应模块位置继续接入真实业务能力，例如训练记录落库、饮食睡眠落库、计划更新和近期总结查询。
