# FitMind 营养计算工具能力契约

## 1. 文档目标

本文档定义 FitMind 从“不精确的自然语言饮食描述”到“可落库的热量和宏量营养估算”所需要的工具能力。

目标不是让 LLM 单独猜测营养值，而是让 LLM 能够按 ReAct 范式调用工具：

```text
用户原始描述
  -> 食物条目解析
  -> 份量和重量估算
  -> 标准食物营养查询
  -> 单项营养计算
  -> 当日营养汇总
  -> 写入 user_nutrition_records
```

---

## 2. 核心原则

### 2.1 LLM 负责理解和编排

LLM 主要负责：

- 识别用户说了哪些食物
- 判断哪些描述是份量
- 在信息不足时决定是否保守估算
- 在 LangGraph ReAct loop 中自主调用合适工具
- 汇总工具结果
- 输出最终 JSON

### 2.2 工具负责可计算事实

工具主要负责：

- 标准化食物名
- 估算生活化份量
- 查询标准营养数据
- 执行数值计算
- 汇总当天总营养

### 2.3 所有工具都要返回置信度

自然语言饮食记录天然不精确，所以工具结果必须包含：

- `confidence`
- `source`
- `warnings`

LLM 需要根据置信度决定：

- 直接采用
- 保守估算
- 提醒用户补充
- 标记为低置信度

---

## 3. 工具总览

第一版推荐实现以下 4 个核心工具：

1. `search_food_nutrition(food_name)`
2. `estimate_food_weight(food_text)`
3. `calculate_nutrition(food_name, amount_g)`
4. `sum_daily_nutrition(items)`

当前代码位置：

```text
agent/src/fitmind_agent/services/nutrition_react_tools.py
```

当前 loop prompt 位置：

```text
agent/src/fitmind_agent/prompts/nutrition_react_loop/
```

当前版本已经内置本地食物营养表和本地份量估算规则，并通过 `LocalMCPNutritionToolProvider` 模拟 MCP 工具边界。

这意味着业务链路不直接依赖本地函数，而是依赖统一工具 provider：

```text
NutritionLangGraphReActRunner
  -> NutritionToolProvider
  -> LocalMCPNutritionToolProvider
  -> NutritionToolRegistry
  -> local tools
```

后续接入外部 MCP 服务时，替换 provider 即可：

```text
NutritionLangGraphReActRunner
  -> MCPNutritionToolProvider
  -> langchain-mcp-adapters / MCP client
  -> nutrition MCP server
```

后续可扩展：

- `parse_food_items(text)`
- `normalize_food_name(food_name)`
- `resolve_food_candidates(food_name)`
- `estimate_meal_nutrition(text)`

---

## 4. 工具一：search_food_nutrition

### 4.1 能力定义

根据食物名称查询标准营养数据。

函数形式：

```text
search_food_nutrition(food_name)
```

用途：

- 将用户输入的食物名映射到标准食物。
- 返回每 100g 或每标准单位的营养数据。
- 支持候选项和置信度。

### 4.2 输入

```json
{
  "food_name": "鸡胸肉"
}
```

字段说明：

- `food_name`
  用户表达或 LLM 标准化后的食物名称。

### 4.3 输出

```json
{
  "query": "鸡胸肉",
  "best_match": {
    "food_id": "local_chicken_breast_cooked",
    "name": "鸡胸肉 熟",
    "alias": ["鸡胸", "熟鸡胸肉"],
    "per_100g": {
      "calories_kcal": 165,
      "protein_g": 31,
      "carbs_g": 0,
      "fat_g": 3.6
    },
    "source": "local_food_database",
    "confidence": 0.92
  },
  "candidates": [
    {
      "food_id": "local_chicken_breast_raw",
      "name": "鸡胸肉 生",
      "confidence": 0.78
    }
  ],
  "warnings": []
}
```

### 4.4 LLM 使用规则

LLM 应该：

- 优先使用 `best_match`
- 如果候选项差异大，结合用户语境选择
- 如果 `confidence < 0.65`，在 `missing_fields` 中提示食物不确定
- 不要把“鸡胸肉 生”和“鸡胸肉 熟”混用而不说明

---

## 5. 工具二：estimate_food_weight

### 5.1 能力定义

将生活化份量描述换算成克或毫升。

函数形式：

```text
estimate_food_weight(food_text)
```

用途：

- 处理“一碗米饭”“一杯牛奶”“一份牛肉”“两个鸡蛋”等表达。
- 返回估算重量、单位和置信度。

### 5.2 输入

```json
{
  "food_text": "一碗米饭",
  "food_name": "米饭"
}
```

字段说明：

- `food_text`
  用户原文中的食物和份量片段。
- `food_name`
  可选，LLM 或上游工具识别出的食物名。

### 5.3 输出

```json
{
  "food_text": "一碗米饭",
  "food_name": "米饭",
  "estimated_amount": {
    "amount_g": 150,
    "unit": "g",
    "portion_label": "一碗",
    "range_g": {
      "min": 120,
      "max": 200
    }
  },
  "source": "portion_size_rules",
  "confidence": 0.76,
  "warnings": [
    "一碗米饭受碗大小影响较大，按常见熟米饭 150g 估算"
  ]
}
```

### 5.4 常见默认估算规则

第一版可以内置常用规则：

| 描述 | 默认估算 |
| --- | --- |
| 一个鸡蛋 | 50g |
| 一杯牛奶 | 250ml，按 250g 计算 |
| 一碗熟米饭 | 150g |
| 一份鸡胸肉 | 150g |
| 一根香蕉 | 120g |
| 一勺蛋白粉 | 30g |
| 一片吐司 | 30g |
| 一杯酸奶 | 180g |

### 5.5 LLM 使用规则

LLM 应该：

- 如果用户给出明确克数，优先使用用户克数
- 如果只有生活化份量，调用该工具估算
- 如果工具返回范围，最终可以采用中位数
- 如果置信度低，保留 `missing_fields` 提醒用户补充重量

---

## 6. 工具三：calculate_nutrition

### 6.1 能力定义

根据食物名和重量计算单项营养摄入。

函数形式：

```text
calculate_nutrition(food_name, amount_g)
```

用途：

- 自动调用或接收 `search_food_nutrition` 的标准营养数据。
- 根据重量计算实际热量、蛋白、碳水、脂肪。

### 6.2 输入

```json
{
  "food_name": "鸡胸肉 熟",
  "amount_g": 200,
  "nutrition_per_100g": {
    "calories_kcal": 165,
    "protein_g": 31,
    "carbs_g": 0,
    "fat_g": 3.6
  }
}
```

### 6.3 输出

```json
{
  "food_name": "鸡胸肉 熟",
  "amount_g": 200,
  "nutrition": {
    "calories_kcal": 330,
    "protein_g": 62,
    "carbs_g": 0,
    "fat_g": 7.2
  },
  "formula": "per_100g * amount_g / 100",
  "source": "local_food_database",
  "confidence": 0.92,
  "warnings": []
}
```

### 6.4 LLM 使用规则

LLM 应该：

- 不手算优先，尽量调用该工具
- 如果用户给的是包装食品营养标签，应优先使用用户标签
- 如果 amount_g 是估算值，最终结果也应该带估算属性

---

## 7. 工具四：sum_daily_nutrition

### 7.1 能力定义

汇总当天所有食物条目的营养数据。

函数形式：

```text
sum_daily_nutrition(items)
```

用途：

- 汇总本轮新增食物
- 或汇总“今天已有记录 + 本轮新增记录”
- 输出今天截至目前的累计热量和宏量营养

### 7.2 输入

```json
{
  "items": [
    {
      "food_name": "鸡蛋",
      "amount_g": 100,
      "nutrition": {
        "calories_kcal": 143,
        "protein_g": 12.6,
        "carbs_g": 0.7,
        "fat_g": 9.5
      }
    },
    {
      "food_name": "牛奶",
      "amount_g": 250,
      "nutrition": {
        "calories_kcal": 150,
        "protein_g": 8,
        "carbs_g": 12,
        "fat_g": 8
      }
    }
  ],
  "existing_daily_total": {
    "calories_kcal": 1200,
    "protein_g": 80,
    "carbs_g": 140,
    "fat_g": 35
  }
}
```

### 7.3 输出

```json
{
  "daily_total": {
    "calories_kcal": 1493,
    "protein_g": 100.6,
    "carbs_g": 152.7,
    "fat_g": 52.5
  },
  "item_count": 2,
  "confidence": 0.84,
  "warnings": [
    "部分食物份量为估算值"
  ]
}
```

### 7.4 LLM 使用规则

LLM 应该：

- 把 `daily_total.calories_kcal` 写入 `calories_estimate`
- 把 `daily_total.protein_g` 写入 `protein_g_estimate`
- 把 `daily_total.carbs_g` 写入 `carbs_g_estimate`
- 把 `daily_total.fat_g` 写入 `fat_g_estimate`

---

## 8. 推荐 ReAct 调用顺序

对于输入：

```text
早餐两个鸡蛋，一杯牛奶，午餐鸡胸肉200g和一碗米饭。
```

推荐调用顺序：

```text
Thought: 用户描述了多个食物，需要先拆分食物条目。
Action: parse_food_items
Observation: 鸡蛋 2个，牛奶 1杯，鸡胸肉 200g，米饭 1碗

Thought: 部分份量不是克数，需要估算重量。
Action: estimate_food_weight("两个鸡蛋")
Action: estimate_food_weight("一杯牛奶")
Action: estimate_food_weight("一碗米饭")

Thought: 已得到食物和重量，需要查询标准营养。
Action: search_food_nutrition("鸡蛋")
Action: search_food_nutrition("牛奶")
Action: search_food_nutrition("鸡胸肉")
Action: search_food_nutrition("米饭")

Thought: 根据每 100g 营养和重量计算单项营养。
Action: calculate_nutrition(...)

Thought: 汇总今日总量。
Action: sum_daily_nutrition(...)

Final: 输出 today_nutrition_record JSON
```

---

## 9. 最终落库 JSON 要求

工具调用结束后，LLM 最终仍然输出当前系统使用的饮食记录 JSON：

```json
{
  "record_date": "2026-06-14",
  "nutrition": {
    "has_content": true,
    "raw_text": "早餐两个鸡蛋，一杯牛奶，午餐鸡胸肉200g和一碗米饭",
    "calories_estimate": 980,
    "protein_g_estimate": 78,
    "carbs_g_estimate": 92,
    "fat_g_estimate": 24
  },
  "confidence": 0.86,
  "missing_fields": [
    "米饭碗大小为估算"
  ],
  "summary_text": "记录早餐和午餐，营养值基于常见份量估算"
}
```

---

## 10. 错误和低置信度处理

### 10.1 食物名不明确

例如：

```text
今天吃了一份套餐。
```

处理方式：

- 工具应返回低置信度
- LLM 不应编造精确营养
- `missing_fields` 中提示需要补充套餐内容

### 10.2 份量不明确

例如：

```text
吃了一些牛肉。
```

处理方式：

- 可以估算“一些”为低置信度范围
- 最终营养字段可以为空或保守估计
- 回复中提示用户补充克数或份量

### 10.3 食物候选冲突

例如：

```text
吃了粉。
```

可能是：

- 米粉
- 河粉
- 蛋白粉

处理方式：

- 返回多个候选
- LLM 结合上下文判断
- 判断不了时不落精确营养，提示用户澄清

---

## 11. MCP 接入建议

每个 MCP 工具建议统一返回：

```json
{
  "ok": true,
  "data": {},
  "confidence": 0.8,
  "source": "mcp_server_name",
  "warnings": []
}
```

失败时返回：

```json
{
  "ok": false,
  "error": {
    "code": "FOOD_NOT_FOUND",
    "message": "未找到匹配食物"
  },
  "confidence": 0,
  "source": "mcp_server_name",
  "warnings": []
}
```

---

## 12. 第一版实现建议

第一版不必直接接复杂外部服务，可以先做本地工具：

1. 建一个小型常见食物营养表
2. 建一个常见份量估算表
3. 实现 `search_food_nutrition`
4. 实现 `estimate_food_weight`
5. 实现 `calculate_nutrition`
6. 实现 `sum_daily_nutrition`
7. 将工具结果注入 `nutrition_tool_context`

这样可以先跑通完整 ReAct 形态，再逐步替换为 MCP 或外部营养数据库。

当前状态：

- 本地常见食物营养表已实现
- 本地份量估算规则已实现
- 四个核心工具已实现
- ReAct engine 已实现
- 饮食记录已改为草稿确认后入库
- 已添加 10 个 ReAct 工具测试用例
