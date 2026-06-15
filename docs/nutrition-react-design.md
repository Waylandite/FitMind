# FitMind 饮食记录 ReAct 工具设计

## 1. 设计目标

饮食记录和身体状态记录已经拆成两个独立意图：

- `today_nutrition_record`
- `today_body_status_record`

拆分原因：

- 饮食记录需要更高精度的热量和宏量营养估算，适合引入工具调用。
- 身体状态记录主要是主观状态、睡眠、体重、疲劳和酸痛，适合轻量 LLM 解析，不需要营养工具。

因此当前设计是：

- 饮食记录走 LangGraph ReAct loop 链路。
- 身体状态记录走普通抽取链路。

具体工具输入输出契约见：

- [nutrition-tools-contract.md](nutrition-tools-contract.md)

---

## 2. 当前已实现链路

当用户意图识别为 `today_nutrition_record` 时：

1. 查询当天已有 `user_nutrition_records`
2. 构建 `daily_context`
3. 启动 `NutritionLangGraphReActRunner`
4. LLM 每轮自主决定调用某个营养工具，或输出最终结构化 JSON
5. LangGraph 负责执行工具节点、写入 observation、判断是否继续循环
6. 达到 `max_iterations` 时强制停止，并基于已有 observation 生成保守草稿
7. 创建 `nutrition_record_drafts` 待确认草稿
8. 用户确认后，将本轮输入带时间刻度追加到 `raw_text`
9. 用户确认后，用最终草稿中的非空营养字段覆盖当天累计字段

确认流程：

- 用户回复“确认保存”后才写入正式饮食表
- 用户可以在确认前继续补充或纠正，例如“牛肉不是一份，是 200g”
- 用户可以回复“取消”放弃本次草稿

当前字段语义：

- `raw_text`
  保存用户原始饮食流水，按时间追加。
- `calories_estimate`
  今天截至目前的累计热量估算。
- `protein_g_estimate`
  今天截至目前的累计蛋白质估算。
- `carbs_g_estimate`
  今天截至目前的累计碳水估算。
- `fat_g_estimate`
  今天截至目前的累计脂肪估算。

---

## 3. 正确 ReAct Loop 设计

FitMind 当前采用经典 ReAct 结构：

```text
Thought / Decide
  -> Action: call tool
  -> Observation: tool result
  -> Thought / Decide
  -> ...
  -> Final: structured nutrition payload
```

在代码中不让服务端硬编码工具顺序，而是让 LLM 输出严格 JSON action：

```json
{
  "action": "tool",
  "tool_name": "search_food_nutrition",
  "arguments": {"food_name": "鸡蛋"},
  "reason": "先查标准营养"
}
```

或者输出最终结果：

```json
{
  "action": "final",
  "payload": {
    "record_date": "2026-06-14",
    "nutrition": {
      "has_content": true,
      "raw_text": "2026-06-14 早餐两个鸡蛋",
      "items": []
    },
    "body_status": {"has_content": false, "raw_text": null},
    "confidence": 0.8,
    "missing_fields": [],
    "summary_text": "记录早餐。"
  }
}
```

Loop 控制由代码负责：

- `max_iterations` 控制最大工具循环次数，默认 8
- `observations` 保存每次工具调用输入、输出和成功状态
- `final_payload` 保存模型最终输出的可确认数据
- 超过循环次数仍未 final 时，系统基于已完成工具观察生成保守草稿
- 所有草稿仍需用户“确认保存”后才写入正式饮食表

当前核心代码：

```text
agent/src/fitmind_agent/services/nutrition_react_tools.py
```

MCP server 入口：

```text
agent/src/fitmind_agent/mcp/nutrition_server.py
```

核心类：

- `NutritionLangGraphReActRunner`
- `LocalMCPNutritionToolProvider`
- `NutritionToolRegistry`

---

## 4. ReAct 工具接入点

当前代码已经实现本地工具注册层：

- `NutritionTool`
- `NutritionToolProvider`
- `NutritionToolRegistry`
- `LocalMCPNutritionToolProvider`
- `NutritionLangGraphReActRunner`

位置：

```text
agent/src/fitmind_agent/services/nutrition_react_tools.py
```

当前 `NutritionToolRegistry` 已内置第一版本地工具，并通过 `NutritionToolProvider` 保留 MCP adapter 扩展协议：

```python
class NutritionToolProvider(Protocol):
    def list_specs(self) -> list[NutritionToolSpec]:
        ...

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ...
```

当前已实现的本地工具：

- `search_food_nutrition`
- `estimate_food_weight`
- `calculate_nutrition`
- `sum_daily_nutrition`

后续 MCP adapter 只需要实现 `NutritionToolProvider` 协议，即可替换当前本地 provider。

推荐替换路径：

```text
LocalMCPNutritionToolProvider
  -> MCPNutritionToolProvider
  -> langchain-mcp-adapters / MCP client
  -> external nutrition MCP server
```

当前仓库已经提供本地 MCP server 入口，暴露：

- `search_food_nutrition`
- `estimate_food_weight`
- `calculate_nutrition`
- `sum_daily_nutrition`

本地开发可在安装依赖后启动：

```bash
cd agent
python -m fitmind_agent.mcp.nutrition_server
```

---

## 5. 推荐工具集合

### `parse_food_items`

用途：

- 将用户自然语言拆成食物条目和份量。

输入示例：

```json
{
  "text": "早餐两个鸡蛋，一杯牛奶，午餐鸡胸肉200g和米饭一碗"
}
```

输出示例：

```json
{
  "items": [
    {"name": "鸡蛋", "amount": 2, "unit": "个"},
    {"name": "牛奶", "amount": 250, "unit": "ml"},
    {"name": "鸡胸肉", "amount": 200, "unit": "g"},
    {"name": "米饭", "amount": 1, "unit": "碗"}
  ]
}
```

### `estimate_food_weight`

用途：

- 将“一碗”“一杯”“一份”等生活化描述换算成克或毫升。

### `search_food_nutrition`

用途：

- 查询标准食物每 100g 的热量、蛋白、碳水和脂肪。

可接入来源：

- 自建食物库
- USDA FoodData Central
- 第三方营养数据库
- MCP 食物营养服务

### `calculate_nutrition`

用途：

- 根据食物重量和每 100g 营养数据计算单项摄入。

### `sum_daily_nutrition`

用途：

- 汇总当天所有食物条目，输出总热量和宏量营养。

---

## 6. 当前 LangGraph 流程

```text
用户输入
  -> 意图识别 today_nutrition_record
  -> 查询当天已有饮食 raw_text 和累计字段
  -> LangGraph: llm_decide
  -> 条件边:
       action=tool 且未超过 max_iterations -> tool_execute
       action=final -> end
       超过 max_iterations -> end + fallback
  -> tool_execute 调用 MCP-ready provider
  -> observation 回灌给 llm_decide
  -> 生成最终累计 JSON
  -> 创建 nutrition_record_drafts
  -> 用户确认
  -> 写入 user_nutrition_records
```

---

## 7. 与身体状态记录的边界

`today_body_status_record` 不接入营养工具。

身体状态只负责：

- 睡眠
- 疲劳
- 压力
- 酸痛
- 体重
- 情绪
- 起床状态
- 健身前后状态
- 恢复状态

其字段语义是：

- `raw_text`
  按时间追加保存用户原始身体状态描述。
- 结构化字段
  保存当天最新非空快照。

---

## 8. 后续实现建议

第一阶段：

- 本地静态食物营养表
- `search_food_nutrition`
- `estimate_food_weight`
- `calculate_nutrition`
- `sum_daily_nutrition`
- 草稿确认后入库

当前状态：已完成。

第二阶段：

- 接入真实 MCP 食物营养服务
- 使用 `langchain-mcp-adapters` 或 MCP client 实现 `MCPNutritionToolProvider`
- 将 `LocalMCPNutritionToolProvider` 替换为远程 MCP provider
- 如 DeepSeek/OpenAI-compatible tool calling 能力稳定，可把 JSON action 协议升级为原生 tool call

第三阶段：

- 新增饮食明细表，记录每个食物条目、重量和营养结果
- 支持用户纠错，例如“刚才鸡胸肉不是 200g，是 150g”
- 支持日报和周报中的营养趋势分析

---

## 9. 参考资料

- ReAct 原始论文：<https://arxiv.org/abs/2210.03629>
- LangChain MCP Adapters：<https://github.com/langchain-ai/langchain-mcp-adapters>

调研结论：

- ReAct 的核心是推理/决策与行动交错执行，行动结果作为 observation 回灌下一轮决策。
- LangGraph 中适合用节点和条件边表达该循环，代码负责终止条件和工具执行，模型负责选择下一步。
- `langchain-mcp-adapters` 可以将 MCP tools 转换为 LangChain tools，并用于 LangGraph agent；FitMind 当前通过 `NutritionToolProvider` 先稳定业务边界，后续替换为真实 MCP provider。
