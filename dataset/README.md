# FitMind Agent 测试数据集

> 本文档定义 FitMind Agent 的测试方法论、数据集格式、评估指标以及批量测试用例的生成策略。

---

## 目录

1. [测试目标](#1-测试目标)
2. [测试能力矩阵](#2-测试能力矩阵)
3. [数据集格式](#3-数据集格式)
4. [评估方法](#4-评估方法)
5. [批量生成策略](#5-批量生成策略)
6. [如何运行测试](#6-如何运行测试)
7. [文件清单](#7-文件清单)

---

## 1. 测试目标

FitMind Agent 的核心任务是将自然语言健身描述转化为结构化数据。测试需要覆盖以下维度：

| 测试维度 | 说明 | 对应文档 |
|---------|------|---------|
| 意图分类 | 是否将用户输入正确归类为 plan / workout / nutrition / body_status / correction / query | `test_cases/intent_classification.jsonl` |
| 事实提取 | 是否从用户输入中正确提取并标准化实体（动作、重量、组次、食物、状态等） | `test_cases/workout_*.jsonl` 等 |
| 多意图分解 | 是否将复合输入正确拆分为多个独立的意图和事实 | `test_cases/multi_intent.jsonl` |
| 纠错理解 | 是否正确理解修改意图、定位目标记录、提取变更内容 | `test_cases/correction.jsonl` |
| 记忆提取 | 是否正确提取用户显式偏好和 Agent 推断画像 | `test_cases/memory_extraction.jsonl` |
| 边界与对抗 | 是否在歧义、不完整、冲突、跨领域关键词等场景下鲁棒 | `test_cases/edge_cases.jsonl` |

---

## 2. 测试能力矩阵

以下是 8 个核心测试能力与对应的 Agent 组件、输出格式的映射关系：

| 编号 | 能力 | 对应 SubAgent | 目标数据表 | 关键输出字段 | 评估模式 |
|------|------|-------------|-----------|-------------|---------|
| C-01 | 意图分类 | Supervisor + Router | `conversation_logs.intent_type` | `intent_type` (enum) | `exact` |
| C-02 | 训练计划提取 | workout_plan_agent | `user_workout_plans` | `plan_date`, `title`, `raw_text`, exercises with sets/reps/weight | `fuzzy` |
| C-03 | 训练结果提取 | workout_result_agent | `user_workout_records` + `user_workout_record_items` | `completion_status`, `perceived_exertion`(1-10), `energy_level`(1-10), `mood`, items | `fuzzy` |
| C-04 | 身体状态提取 | condition_agent | `user_body_status_records` | `sleep_hours`, `fatigue_level`(1-10), `stress_level`(1-10), `soreness_level`(1-10), `body_weight_kg`, `mood` | `fuzzy` |
| C-05 | 饮食提取 | nutrition_agent | `user_nutrition_records` | `meal_type`, food items, portions, supplements, macro estimates | `fuzzy` |
| C-06 | 纠错理解 | correction_agent | (any via PATCH) | 目标记录, 变更字段, 旧值, 新值, 变更原因 | `fuzzy` |
| C-07 | 多意图分解 | Supervisor + Router | (multiple) | `intent_bundle` + per-intent facts | `partial` |
| C-08 | 记忆提取 | Memory System | `user_defined_memories` + `agent_derived_memories` | `memory_category`, `memory_key`, `memory_value`, `confidence_score` | `fuzzy` |

---

## 3. 数据集格式

### 3.1 文件格式

所有测试用例使用 **JSONL**（JSON Lines）格式：

- 每行一个完整的 JSON 对象
- UTF-8 编码，无 BOM
- 每个 JSON 对象必须符合 `schemas/test_case_schema.json` 定义的 JSON Schema
- 空行自动忽略
- 以 `//` 开头的行视为注释（用于标注和说明）

### 3.2 测试用例结构

每条测试用例包含以下字段：

```json
{
  "test_id": "INT-001",
  "category": "intent_classification",
  "subcategory": "happy_path",
  "input": "今天练胸，卧推60kg 5x5",
  "expected": {
    "intent_type": "workout",
    "intent_bundle": ["workout"],
    "facts": [...],
    "memory_keys": [...]
  },
  "evaluation_mode": "exact",
  "notes": "标准单意图输入",
  "tags": ["single_intent", "exercise_weight_sets_reps"]
}
```

### 3.3 测试 ID 命名规范

| 前缀 | 能力 | 示例 |
|------|------|------|
| `INT` | 意图分类 | INT-001 |
| `WPL` | 训练计划提取 | WPL-001 |
| `WOR` | 训练结果提取 | WOR-001 |
| `BOD` | 身体状态提取 | BOD-001 |
| `NUT` | 饮食提取 | NUT-001 |
| `COR` | 纠错理解 | COR-001 |
| `MUL` | 多意图分解 | MUL-001 |
| `MEM` | 记忆提取 | MEM-001 |
| `EDG` | 边界/对抗用例 | EDG-001 |

### 3.4 评估模式说明

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `exact` | 输出必须与期望完全一致（字段级别） | 意图分类、枚举值匹配 |
| `fuzzy` | 输出与期望语义等价即可，允许合理的表述差异 | 事实提取、实体识别 |
| `partial` | 期望的事实必须是实际输出事实的子集（允许额外输出） | 多意图分解、复杂场景 |

详细规范见：`schemas/test_case_schema.md`

---

## 4. 评估方法

### 4.1 评估指标总览

| 指标 | 公式/方法 | 目标 |
|------|----------|------|
| 意图分类准确率 | `correct / total` | > 90% |
| 实体 F1 分数 | `2 × P × R / (P + R)` | > 85% |
| 字段级准确率 | 按字段类型分别评估（字符串精确、数值容差） | > 80% |
| 置信度校准 | Expected Calibration Error (ECE) | < 0.1 |
| 纠错准确率 | 目标识别 ∧ 字段识别 ∧ 值提取 全对 | > 80% |
| 多意图召回率 | `detected_intents / total_expected_intents` | > 85% |
| 记忆提取准确率 | 分类准确率 + 字段相似度 | > 80% |

### 4.2 字段级评估规则

- **字符串字段**（枚举值如 `intent_type`, `completion_status`）：精确匹配
- **字符串字段**（自由文本如 `exercise_name`, `raw_text`）：语义等价或包含关系
- **数值字段**（如 `weight_kg`）：容差 ±2.5kg
- **数值字段**（如 `sets`, `reps`）：精确匹配
- **范围字段**（如 `perceived_exertion`, `energy_level` 1-10）：容差 ±1
- **`raw_text` 字段**：必须存在于输出中（存在性检查，不要求精确匹配）

完整评估细则见：`evaluation/metrics.md`

### 4.3 评估流程

```
1. 加载测试文件（JSONL）
2. 对每条测试用例：
   a. 将 input 发送给 Agent
   b. 获取 Agent 的结构化输出
   c. 根据 evaluation_mode 选择比较策略
   d. 记录匹配/不匹配/部分匹配
3. 汇总统计：
   - 按 capability 分组计算各指标
   - 按 subcategory 分析薄弱环节
   - 生成评估报告（per-case + aggregate）
```

---

## 5. 批量生成策略

测试用例可以通过以下方法批量扩展：

1. **模板组合生成**：定义动作词表（50+）、重量列表（11 个常见值）、组次模式（6 种），笛卡尔积组合产生 3,300+ 训练用例
2. **同义词扩展**：对每个实体映射中文变体（如 卧推/杠铃卧推/bench press），对意图关键词扩展同义表达
3. **数据增强**：添加填充词（"嗯"、"然后"）、时间变换（"今天"→"昨天"→"周一"）、量词变换（"60kg"→"60公斤"→"六十公斤"）、事实顺序排列
4. **对抗样本**：构造否定句、跨领域关键词混淆、自纠错、中英混合、英制单位等挑战性输入

完整策略见：`generation/generation_strategy.md`

---

## 6. 如何运行测试

### 6.1 前置条件

- FitMind Agent 服务已启动（或可导入）
- Python 3.11+ 环境
- 安装项目依赖：`pip install -e agent/`

### 6.2 运行方式

测试运行器位于 `agent/tests/test_dataset.py`（需要独立实现）：

```bash
# 运行所有测试用例
python -m pytest agent/tests/test_dataset.py -v

# 仅运行特定能力的测试
python -m pytest agent/tests/test_dataset.py -v -k "intent"

# 生成详细评估报告
python agent/tests/test_dataset.py --report-format json --output results.json
```

### 6.3 验证测试用例格式

```bash
# 使用 jsonschema 验证所有 JSONL 文件
python -c "
import json
from jsonschema import validate

# 加载 schema
with open('dataset/schemas/test_case_schema.json') as f:
    schema = json.load(f)

# 验证每个 JSONL 文件
# ...
"
```

---

## 7. 文件清单

| 文件路径 | 说明 |
|---------|------|
| `README.md` | 本文件：测试方法论总览 |
| `schemas/test_case_schema.json` | JSON Schema (draft-07)：测试用例格式定义 |
| `schemas/test_case_schema.md` | 人工可读的 schema 文档，含字段说明和示例 |
| `formats/jsonl_format.md` | JSONL 文件格式规范 |
| `evaluation/metrics.md` | 详细评分细则：每项能力的评估指标和阈值 |
| `evaluation/scoring_calculator.py` | 参考评估算法实现 |
| `generation/generation_strategy.md` | 系统化生成批量测试用例的策略 |
| `generation/templates/workout_templates.md` | 训练相关模板和变量组合 |
| `generation/templates/nutrition_templates.md` | 饮食相关模板和食物词表 |
| `generation/templates/body_status_templates.md` | 身体状态描述模板 |
| `generation/templates/correction_templates.md` | 纠错场景模板 |
| `generation/augmentation/synonym_map.md` | 健身领域中文同义词/变体映射表 |
| `generation/augmentation/adversarial_patterns.md` | 对抗性样本设计模式 |
| `test_cases/intent_classification.jsonl` | 意图分类测试用例（8 条） |
| `test_cases/workout_plan.jsonl` | 训练计划提取测试用例（5 条） |
| `test_cases/workout_result.jsonl` | 训练结果提取测试用例（5 条） |
| `test_cases/body_status.jsonl` | 身体状态提取测试用例（5 条） |
| `test_cases/nutrition.jsonl` | 饮食提取测试用例（5 条） |
| `test_cases/correction.jsonl` | 纠错理解测试用例（5 条） |
| `test_cases/multi_intent.jsonl` | 多意图分解测试用例（5 条） |
| `test_cases/memory_extraction.jsonl` | 记忆提取测试用例（5 条） |
| `test_cases/edge_cases.jsonl` | 跨能力边界用例（6 条） |

---
