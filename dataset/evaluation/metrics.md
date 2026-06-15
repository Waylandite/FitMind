# FitMind Agent 评估指标详解

> 本文档定义针对每种 Agent 能力的详细评分细则、阈值和计算方法。

---

## 1. 评估策略总览

测试评估分为 4 个层级：

| 层级 | 范围 | 说明 |
|------|------|------|
| **用例级** | 单个测试用例 | 该用例的匹配结果：pass / fail / partial |
| **能力级** | 一个 capability 的所有用例 | 意图分类准确率、实体 F1 等 |
| **场景级** | 一个 subcategory 的所有用例 | 按场景类型聚合（happy_path / edge_case 等） |
| **全局** | 所有测试用例 | 综合能力评分 |

---

## 2. 意图分类（Capability 1）

### 2.1 指标：`intent_accuracy`

```
intent_accuracy = N_correct / N_total
```

- 评估模式：`exact`
- 预测的 `intent_type` 必须与期望的 `intent_type` 精确相等

### 2.2 多意图扩展指标：`decomposition_recall`

```
decomposition_recall = | predicted_intents ∩ expected_intents | / | expected_intents |
```

- 评估模式：`partial`
- 适用多意图测试（`MUL-*` 用例）
- 检测到的意图集合包含期望集合中的所有元素即算通过

### 2.3 阈值

| 子场景 | 目标准确率 |
|--------|----------|
| happy_path | > 95% |
| edge_case / ambiguous | > 80% |
| adversarial | > 70% |
| 总平均 | > 90% |

---

## 3. 事实提取（Capabilities 2-5）

### 3.1 实体级 F1 分数

对于每条测试用例，按以下步骤计算：

**步骤 1：匹配事实对**

将 Agent 输出的 `facts` 数组与期望的 `facts` 数组进行匹配：

- 基于 `fact_type` 和 `raw_text` 进行匹配
- 使用编辑距离（Levenshtein）最近的原则建立对应关系
- 一个期望 fact 最多匹配一个实际 fact

**步骤 2：计数**

```
TP = 匹配成功的期望 fact 数量
FP = 实际输出中无法匹配到期望 fact 的数量
FN = 期望 fact 中未能匹配的数量
```

**步骤 3：计算 F1**

```
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 × P × R / (P + R)
```

### 3.2 字段级准确率

对于每个匹配的 fact 对，比较 `normalized_payload` 内的字段：

| 字段类型 | 比较方法 | 阈值 |
|---------|---------|------|
| 枚举字符串（如 `completion_status`） | 精确匹配 | 100% |
| 自由字符串（如 `exercise_name`） | 语义匹配（同义词映射） | 可接受变体 |
| 整数（如 `sets`, `reps`） | 精确匹配 | ±0 |
| 重量（如 `weight_kg`） | 绝对容差 | ±2.5kg |
| 浮点（如 `sleep_hours`） | 绝对容差 | ±0.5h |
| 范围评分（如 `fatigue_level` 1-10） | 绝对容差 | ±1 |
| `raw_text` | 存在性检查 | 必须存在 |

**字段级准确率** = 匹配的字段数 / 总需匹配的字段数

### 3.3 阈值

| 指标 | 目标 |
|------|------|
| 实体 F1（happy_path） | > 90% |
| 实体 F1（edge_case） | > 75% |
| 实体 F1（总平均） | > 85% |
| 字段级准确率（总平均） | > 80% |

---

## 4. 置信度校准（Capability 2-5）

### 4.1 指标：Expected Calibration Error (ECE)

```
ECE = Σ_{b=1}^{B} (N_b / N) × | acc_b - conf_b |
```

其中：
- `B` = 置信度分桶数（如 5 个桶：0-0.2, 0.2-0.4, ..., 0.8-1.0）
- `N_b` = 桶 b 中的预测数量
- `N` = 总预测数量
- `acc_b` = 桶 b 中的实际准确率
- `conf_b` = 桶 b 的平均置信度

### 4.2 阈值

| 指标 | 目标 |
|------|------|
| ECE | < 0.10 |

---

## 5. 纠错准确率（Capability 6）

### 5.1 子指标

纠错能力评估三个子维度，整体通过要求全部满足：

| 子指标 | 说明 | 评估方法 |
|--------|------|---------|
| `target_identified` | 是否正确识别了要修改的目标记录 | 目标定位字段匹配（如 `target_exercise`） |
| `field_identified` | 是否正确识别了要修改的字段 | `field_to_change` 匹配 |
| `value_extracted` | 修改后的值是否正确 | 新值的 fuzzy 匹配 |

### 5.2 综合准确率

```
correction_accuracy = (target_correct ∧ field_correct ∧ value_correct) / N_total
```

### 5.3 阈值

| 指标 | 目标 |
|------|------|
| 综合纠错准确率 | > 80% |

---

## 6. 多意图分解（Capability 7）

### 6.1 指标

```
decomposition_recall = | detected_intents ∩ expected_intents | / | expected_intents |
decomposition_precision = | detected_intents ∩ expected_intents | / | detected_intents |
```

### 6.2 事实归属检查

对于检测到的每个意图，检查其关联的事实是否与期望一致：
- 每个期望的 fact 至少被一条实际 fact 覆盖

### 6.3 阈值

| 指标 | 目标 |
|------|------|
| decomposition_recall | > 85% |
| decomposition_precision | > 80% |
| fact_coverage | > 85% |

---

## 7. 记忆提取（Capability 8）

### 7.1 指标

| 子指标 | 评估方法 |
|--------|---------|
| `category_accuracy` | 预测的 `memory_category` 是否在期望集合中 |
| `key_accuracy` | 预测的 `memory_key` 是否语义匹配 |
| `value_similarity` | 使用 ROUGE-L 计算 `memory_value` 文本相似度 |

### 7.2 综合评分

```
memory_score = category_accuracy × 0.3 + key_accuracy × 0.3 + value_similarity × 0.4
```

### 7.3 阈值

| 指标 | 目标 |
|------|------|
| category_accuracy | > 90% |
| key_accuracy | > 80% |
| value_similarity (ROUGE-L) | > 0.75 |
| memory_score | > 80% |

---

## 8. 综合评分

### 8.1 全局评分公式

```
global_score = intent_accuracy × 0.15
             + entity_f1 × 0.30
             + field_accuracy × 0.15
             + correction_accuracy × 0.10
             + decomposition_recall × 0.10
             + memory_score × 0.10
             + ece_penalty × 0.10
```

其中 `ece_penalty = max(0, 1 - ECE)`。

### 8.2 通过标准

| 全局评分 | 评级 |
|---------|------|
| > 90% | 优秀 |
| > 80% | 良好 |
| > 70% | 及格 |
| < 70% | 需改进 |

---

## 9. 错误分类与分析

建议将错误分为以下几类：

| 错误类型 | 说明 | 典型原因 |
|---------|------|---------|
| `MISSED_FACT` | 期望的事实未被提取 | 模型忽略或遗漏字段 |
| `HALLUCINATED_FACT` | 输出了不存在于输入中的事实 | 模型过度推断 |
| `WRONG_CLASSIFICATION` | 意图或事实类型分类错误 | 模型理解偏差 |
| `WRONG_VALUE` | 提取的值不正确 | 模型解析错误 |
| `WRONG_NORMALIZATION` | 标准化后的值不正确 | 归一化逻辑缺陷 |
| `MISSING_RAWTEXT` | 输出了事实但丢失了原始文本 | raw_text 未保留 |
| `CONFIDENCE_MISCALIBRATED` | 置信度与正确率不匹配 | 模型信心评估不准 |

每轮测试后应生成错误分布报告，用于识别系统薄弱环节。

---

## 10. 报告模板

建议每轮评估输出以下格式的报告：

```json
{
  "evaluation_date": "2026-06-11",
  "total_cases": 49,
  "passed": 42,
  "failed": 5,
  "partial": 2,
  "global_score": 0.85,
  "by_capability": {
    "intent_classification": { "accuracy": 0.93, "cases": 8 },
    "workout_plan": { "entity_f1": 0.88, "field_accuracy": 0.85, "cases": 5 },
    "workout_result": { "entity_f1": 0.87, "field_accuracy": 0.83, "cases": 5 },
    "body_status": { "entity_f1": 0.90, "field_accuracy": 0.88, "cases": 5 },
    "nutrition": { "entity_f1": 0.85, "field_accuracy": 0.82, "cases": 5 },
    "correction": { "accuracy": 0.80, "cases": 5 },
    "multi_intent": { "recall": 0.88, "precision": 0.85, "cases": 5 },
    "memory_extraction": { "memory_score": 0.82, "cases": 5 },
    "edge_case": { "entity_f1": 0.75, "cases": 6 }
  },
  "by_subcategory": {
    "happy_path": { "score": 0.92, "cases": 20 },
    "edge_case": { "score": 0.78, "cases": 15 },
    "ambiguous": { "score": 0.75, "cases": 4 },
    "adversarial": { "score": 0.70, "cases": 5 },
    "multi_intent": { "score": 0.85, "cases": 5 }
  },
  "error_distribution": {
    "MISSED_FACT": 3,
    "HALLUCINATED_FACT": 2,
    "WRONG_VALUE": 4,
    "WRONG_NORMALIZATION": 1,
    "CONFIDENCE_MISCALIBRATED": 2
  },
  "ece": 0.08
}
```
