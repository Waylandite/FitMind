# 测试用例 Schema 文档

> 本文档是 `test_case_schema.json` 的人工可读版本，包含每个字段的详细说明、示例和设计理由。

---

## 1. 顶层结构

每条测试用例是一个 JSON 对象，必须包含以下必填字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `test_id` | `string` | 是 | 唯一标识符，格式 `XXX-NNN`（3 字母前缀 + 3 位数字） |
| `category` | `string` (enum) | 是 | 所属测试能力类别 |
| `input` | `string` | 是 | 用户输入的原始文本（中文为主） |
| `expected` | `object` | 是 | 期望的 Agent 结构化输出 |
| `evaluation_mode` | `string` (enum) | 是 | 评估策略：`exact` / `fuzzy` / `partial` |

可选字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `subcategory` | `string` (enum) | 测试场景子类型，用于分组和分析 |
| `notes` | `string` | 测试用例说明、预期行为和特殊注意事项 |
| `tags` | `array[string]` | 自由标签，用于筛选和分组 |

---

## 2. 字段详细说明

### 2.1 `test_id` — 测试用例 ID

**格式**：`{CAPABILITY_PREFIX}-{SEQUENCE_NUMBER}`

**前缀映射**：

| 前缀 | 能力 | 对应 JSONL 文件 |
|------|------|----------------|
| `INT` | 意图分类 | `intent_classification.jsonl` |
| `WPL` | 训练计划提取 | `workout_plan.jsonl` |
| `WOR` | 训练结果提取 | `workout_result.jsonl` |
| `BOD` | 身体状态提取 | `body_status.jsonl` |
| `NUT` | 饮食提取 | `nutrition.jsonl` |
| `COR` | 纠错理解 | `correction.jsonl` |
| `MUL` | 多意图分解 | `multi_intent.jsonl` |
| `MEM` | 记忆提取 | `memory_extraction.jsonl` |
| `EDG` | 边界/对抗用例 | `edge_cases.jsonl` |

**序列号**：三位数字，从 001 递增。同一文件内不重复。

---

### 2.2 `category` — 测试类别

枚举值，必须与测试文件对应：

```
intent_classification | workout_plan | workout_result | body_status |
nutrition | correction | multi_intent | memory_extraction | edge_case
```

---

### 2.3 `subcategory` — 测试场景子类型

| 子类型 | 说明 | 典型用例 |
|--------|------|---------|
| `happy_path` | 标准、完整、无歧义的正常输入 | 完整记录一次训练、标准饮食日记 |
| `edge_case` | 边界场景，输入不完整或特殊 | 只有体重没有其他字段、单天多餐合并 |
| `ambiguous` | 输入有歧义，需要 Agent 判别人机交互 | 单个词"深蹲"、模糊指代"和昨天一样" |
| `incomplete` | 信息缺失，部分字段无法填充 | 只说"练完了"不说细节 |
| `conflicting` | 输入中包含矛盾信息 | 说练了又说没去健身房 |
| `multi_intent` | 一条消息包含多个意图 | 训练+饮食+状态混合 |
| `correction` | 对自己的前序输入进行修改 | "改成55kg" |
| `adversarial` | 专门设计的对抗性输入 | 否定句、跨领域关键词混淆、中英混合 |

---

### 2.4 `input` — 用户输入

- 类型：字符串
- 语言：中文为主，可包含英文或中英混合
- 长度：最少 1 个字符
- 内容：模拟真实用户的自然语言健身描述

**示例**：

```json
"今天练胸，卧推60kg 5x5，上斜哑铃推举4组12次，状态还不错"
```

```json
"把刚才的深蹲改成80kg，不是60kg"
```

---

### 2.5 `expected` — 期望输出

Agent 应该输出的结构化结果。根据测试类别不同，`expected` 内部字段会有所侧重：

#### 2.5.1 `expected.intent_type`

- 类型：`string` (enum)
- 枚举值：`plan | workout | nutrition | body_status | correction | query | unknown`
- 对应 `conversation_logs.intent_type` 的 CHECK 约束
- 用于意图分类测试（Capability 1），评估模式为 `exact`

#### 2.5.2 `expected.intent_bundle`

- 类型：`array[string]`
- 用于多意图测试（Capability 7）
- 包含 Agent 应检测到的所有意图

#### 2.5.3 `expected.facts`

- 类型：`array[object]`
- 每个 fact 对象包含：

```json
{
  "fact_type": "completed_exercise",
  "raw_text": "卧推60kg 5x5",
  "normalized_payload": {
    "exercise_name": "卧推",
    "weight_kg": 60,
    "sets": 5,
    "reps": 5
  },
  "confidence": 0.95
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fact_type` | `string` | 事实类别：`planned_exercise`, `completed_exercise`, `completed_cardio`, `sleep`, `fatigue`, `stress`, `soreness`, `body_weight`, `mood`, `meal`, `supplement`, `correction`, `perceived_exertion`, `energy_level`, `completion_status` |
| `raw_text` | `string` | 从用户输入中提取的原文片段。**必须保留原始文本，不可丢失。** |
| `normalized_payload` | `object` | 标准化后的结构化数据。不同 `fact_type` 的 payload 结构不同： |
| `confidence` | `number` (0-1) | 提取可信度 |

**各类 fact 的 normalized_payload 参考字段**：

| fact_type | normalized_payload 典型字段 |
|-----------|---------------------------|
| `planned_exercise` / `completed_exercise` | `exercise_name`, `weight_kg`, `sets`, `reps`, `completed` (bool) |
| `completed_cardio` | `exercise_name`, `duration_minutes`, `distance_km` |
| `sleep` | `sleep_hours` |
| `fatigue` | `fatigue_level` (1-10) |
| `stress` | `stress_level` (1-10) |
| `soreness` | `soreness_level` (1-10), `location` |
| `body_weight` | `body_weight_kg` |
| `mood` | `mood` (string) |
| `meal` | `meal_type`, `foods` (array), `protein_g_estimate`, `carbs_g_estimate`, `fat_g_estimate`, `calories_estimate` |
| `supplement` | `supplement_name`, `timing`, `protein_g_estimate` |
| `correction` | `target_exercise`, `field_to_change`, `old_value`, `new_value`, `reason` |
| `perceived_exertion` | `perceived_exertion` (1-10) |
| `energy_level` | `energy_level` (1-10) |
| `completion_status` | `completion_status` (completed/partial/skipped) |

#### 2.5.4 `expected.memory_keys`

- 类型：`array[object]`
- 用于记忆提取测试（Capability 8）
- 每个 memory 对象包含：

```json
{
  "memory_category": "fitness_preference",
  "memory_key": "goal_type",
  "memory_value": "减脂"
}
```

**`memory_category` 枚举值**：

用户显式记忆（`user_defined_memories`）：
- `fitness_preference`：健身偏好
- `content_preference`：内容偏好
- `conversation_preference`：对话风格
- `diet_preference`：饮食约束
- `health_constraint_preference`：健康限制

Agent 推断记忆（`agent_derived_memories`）：
- `fitness_goal_memory`：健身目标
- `training_pattern_memory`：训练模式
- `exercise_preference_memory`：动作偏好
- `body_status_baseline_memory`：身体状态基线
- `nutrition_pattern_memory`：饮食模式
- `conversation_style_memory`：交互风格
- `current_phase_memory`：当前阶段
- `adherence_risk_memory`：执行风险

---

### 2.6 `evaluation_mode` — 评估模式

| 模式 | 说明 | 何时使用 |
|------|------|---------|
| `exact` | 输出必须与期望精确匹配。字符串精确匹配，数值精确匹配。 | 意图分类（单一枚举值）、有限选项的字段 |
| `fuzzy` | 输出与期望语义等价即可。允许不同的表述（如"杠铃卧推" vs "卧推"），数值允许容差（重量 ±2.5kg，主观评分 ±1）。 | 实体提取、事实提取（LLM 输出有一定变化） |
| `partial` | 期望的事实必须是实际输出事实的子集。Agent 可以额外输出更多内容，但不能遗漏期望的核心事实。 | 多意图分解（边界划分可能不同）、复杂复合输入 |

---

## 3. 完整示例

### 示例 1：单意图训练记录（exact 模式）

```json
{
  "test_id": "INT-001",
  "category": "intent_classification",
  "subcategory": "happy_path",
  "input": "今天练腿，深蹲80kg 3x5，腿举120kg 4x10",
  "expected": {
    "intent_type": "workout"
  },
  "evaluation_mode": "exact",
  "notes": "标准训练记录输入",
  "tags": ["single_intent", "exercise_weight_sets_reps"]
}
```

### 示例 2：训练事实提取（fuzzy 模式）

```json
{
  "test_id": "WOR-001",
  "category": "workout_result",
  "subcategory": "happy_path",
  "input": "今天练胸，卧推60kg 5x5，上斜哑铃推举4组12次，状态还不错",
  "expected": {
    "facts": [
      {
        "fact_type": "completed_exercise",
        "raw_text": "卧推60kg 5x5",
        "normalized_payload": {
          "exercise_name": "卧推",
          "weight_kg": 60,
          "sets": 5,
          "reps": 5,
          "completed": true
        },
        "confidence": 0.95
      },
      {
        "fact_type": "completed_exercise",
        "raw_text": "上斜哑铃推举4组12次",
        "normalized_payload": {
          "exercise_name": "上斜哑铃推举",
          "sets": 4,
          "reps": 12,
          "completed": true
        },
        "confidence": 0.90
      },
      {
        "fact_type": "mood",
        "raw_text": "状态还不错",
        "normalized_payload": {
          "mood": "良好"
        },
        "confidence": 0.80
      }
    ]
  },
  "evaluation_mode": "fuzzy",
  "tags": ["standard_workout", "mood"]
}
```

### 示例 3：多意图输入（partial 模式）

```json
{
  "test_id": "MUL-001",
  "category": "multi_intent",
  "subcategory": "multi_intent",
  "input": "今天练了腿，深蹲80kg 3x5，睡了7小时，晚饭吃了牛排",
  "expected": {
    "intent_bundle": ["workout", "body_status", "nutrition"],
    "facts": [
      {
        "fact_type": "completed_exercise",
        "raw_text": "深蹲80kg 3x5"
      },
      {
        "fact_type": "sleep",
        "raw_text": "睡了7小时"
      },
      {
        "fact_type": "meal",
        "raw_text": "晚饭吃了牛排"
      }
    ]
  },
  "evaluation_mode": "partial",
  "tags": ["three_intents", "workout_body_nutrition"]
}
```

---

## 4. 字段对应关系总结

以下是测试用例 `expected` 字段与数据库表 / CHECK 约束的对应关系：

| 测试字段 | 对应 DB 字段 / 约束 | 来源文件 |
|---------|-------------------|---------|
| `intent_type` | `conversation_logs.intent_type` CHECK 约束 | `db/models.py:98` |
| `fact.exercise_name` | `user_workout_record_items.exercise_name` | `db/models.py:152` |
| `fact.weight_kg` | `user_workout_record_items.weight_text` (转为数值) | `db/models.py:156` |
| `fact.sets/reps` | `user_workout_record_items.sets_count` / `reps_text` | `db/models.py:153-154` |
| `fact.completion_status` | `user_workout_records.completion_status` CHECK 约束 | `db/models.py:136` |
| `fact.perceived_exertion` | `user_workout_records.perceived_exertion` (1-10) | `db/models.py:137-138` |
| `fact.sleep_hours` | `user_body_status_records.sleep_hours` | `db/models.py:184` |
| `fact.fatigue_level` | `user_body_status_records.fatigue_level` (1-10) | `db/models.py:185` |
| `fact.soreness_level` | `user_body_status_records.soreness_level` (1-10) | `db/models.py:187` |
| `fact.meal_type` | `user_nutrition_records.raw_text` (转为结构化) | `db/models.py:172` |
| `fact.protein_g_estimate` | `user_nutrition_records.protein_g_estimate` | `db/models.py:174` |
| `memory_category` | `user_defined_memories.memory_category` CHECK | `db/models.py:233` |
| `memory_category` (agent) | `agent_derived_memories.memory_category` CHECK | `db/models.py:267` |

---
