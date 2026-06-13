# FitMind 饮食记录 ReAct 工具设计

## 1. 设计目标

饮食记录和身体状态记录已经拆成两个独立意图：

- `today_nutrition_record`
- `today_body_status_record`

拆分原因：

- 饮食记录需要更高精度的热量和宏量营养估算，适合引入工具调用。
- 身体状态记录主要是主观状态、睡眠、体重、疲劳和酸痛，适合轻量 LLM 解析，不需要营养工具。

因此当前设计是：

- 饮食记录走 ReAct-ready 链路。
- 身体状态记录走普通抽取链路。

---

## 2. 当前已实现链路

当用户意图识别为 `today_nutrition_record` 时：

1. 查询当天已有 `user_nutrition_records`
2. 构建 `daily_context`
3. 构建 `nutrition_tool_context`
4. 调用 `nutrition_record_extraction` Prompt
5. 输出今天截至目前的累计营养 JSON
6. 将本轮输入带时间刻度追加到 `raw_text`
7. 用 LLM 输出的非空营养字段覆盖当天累计字段

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

## 3. ReAct 工具接入点

当前代码已经预留工具注册层：

- `NutritionTool`
- `NutritionToolRegistry`
- `NutritionReActToolContextBuilder`

位置：

```text
agent/src/fitmind_agent/services/nutrition_react_tools.py
```

当前 `NutritionToolRegistry` 还没有绑定具体 MCP 服务，但已经定义了统一协议：

```python
class NutritionTool(Protocol):
    name: str
    description: str

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        ...
```

后续 MCP adapter 只需要实现该协议，即可注册进饮食记录链路。

---

## 4. 推荐工具集合

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

## 5. 推荐 ReAct 流程

```text
用户输入
  -> 意图识别 today_nutrition_record
  -> 查询当天已有饮食 raw_text 和累计字段
  -> LLM 拆分食物条目
  -> 调用 parse_food_items
  -> 调用 estimate_food_weight
  -> 调用 search_food_nutrition
  -> 调用 calculate_nutrition
  -> 调用 sum_daily_nutrition
  -> LLM 生成最终累计 JSON
  -> 写入 user_nutrition_records
```

---

## 6. 与身体状态记录的边界

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

## 7. 后续实现建议

第一阶段：

- 增加本地静态食物营养表
- 实现 `search_food_nutrition`
- 实现 `calculate_nutrition`

第二阶段：

- 接入 MCP 食物营养服务
- 将工具结果写入 `nutrition_tool_context`
- 让 LLM 基于工具结果生成最终累计 JSON

第三阶段：

- 新增饮食明细表，记录每个食物条目、重量和营养结果
- 支持用户纠错，例如“刚才鸡胸肉不是 200g，是 150g”
- 支持日报和周报中的营养趋势分析
