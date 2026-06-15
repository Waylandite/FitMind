# Token 使用统计设计

## 目标

FitMind 需要统计每轮用户对话和每次 LLM 调用的 token 消耗，用于测试、成本分析和链路排查。统计逻辑必须是旁路能力：写入失败不影响聊天、意图识别、草稿确认和业务落库。

## 表设计

### `llm_call_logs`

记录每一次真实模型调用。一次用户对话可能包含多次调用，例如意图识别、营养 ReAct 决策、草稿提取、普通聊天回复、summary 压缩。

核心字段：

- `request_id`：一轮用户对话的链路 ID。
- `workflow`：业务链路，例如 `intent`、`nutrition_record`、`chat`、`summary`。
- `node_name`：具体节点，例如 `intent_classifier`、`generate_text`、`chat_stream`。
- `model` / `provider`：模型类型和供应商。
- `is_stream`：是否为流式调用。
- `prompt_tokens`：输入 token。
- `completion_tokens`：输出 token。
- `total_tokens`：总 token。
- `reasoning_tokens` / `cached_tokens`：供应商返回时记录。
- `usage_source`：`provider`、`estimated`、`unavailable`。
- `latency_ms`：模型调用耗时。
- `success` / `error_message`：调用状态。
- `raw_usage`：供应商原始 usage JSON。

### `chat_turn_token_usage`

记录一轮用户对话聚合消耗。它按 `request_id` 汇总 `llm_call_logs`。

核心字段：

- `request_id`：一轮对话 ID，唯一。
- `user_id` / `thread_id` / `session_id`：归属关系。
- `intent_type`：本轮最终意图类型。
- `model_breakdown`：按模型聚合的 JSON。
- `total_prompt_tokens`：本轮所有模型调用输入 token。
- `total_completion_tokens`：本轮所有模型调用输出 token。
- `total_tokens`：本轮总 token。
- `llm_call_count`：本轮模型调用次数。

## 写入策略

1. `ChatService` 在每轮对话入口生成 `request_id`，写入 context。
2. `DeepSeekLLMClient` 每次调用完成后提取 API 返回的 `usage`。
3. `TokenUsageTracker` 使用线程池异步写入 `llm_call_logs`。
4. 一轮对话结束后，`ChatService` 异步汇总同一 `request_id` 的调用明细，写入 `chat_turn_token_usage`。
5. 所有写入异常只记录日志，不向主业务抛出。

## 注意

流式调用只有供应商返回 usage 时才能准确统计；如果没有 usage，则记录 `usage_source=unavailable`，避免用不准确估算冒充真实账单。
