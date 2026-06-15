"""
FitMind Agent 测试评估算法参考实现

本文件提供评估计算的参考算法，用于指导实际的测试运行器实现。
实际测试运行器应放在 agent/tests/test_dataset.py 中。

用法示例：
    calculator = ScoringCalculator("dataset/test_cases/intent_classification.jsonl")
    report = calculator.evaluate(agent_outputs)
    print(report.to_json())
"""

import json
import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 字段比较规则
# ---------------------------------------------------------------------------

# 数值容差
WEIGHT_TOLERANCE_KG = 2.5
EXERTION_TOLERANCE = 1
SLEEP_TOLERANCE_HOURS = 0.5

# 需要精确匹配的字段（枚举值、标识符）
EXACT_MATCH_FIELDS = {"fact_type", "completion_status", "intent_type"}

# 需要语义匹配的字段（自由文本）
FUZZY_MATCH_FIELDS = {"exercise_name", "mood", "meal_type", "raw_text"}

# 需要数值容差匹配的字段
NUMERIC_FIELDS = {
    "weight_kg": WEIGHT_TOLERANCE_KG,
    "perceived_exertion": EXERTION_TOLERANCE,
    "energy_level": EXERTION_TOLERANCE,
    "fatigue_level": EXERTION_TOLERANCE,
    "stress_level": EXERTION_TOLERANCE,
    "soreness_level": EXERTION_TOLERANCE,
    "sleep_hours": SLEEP_TOLERANCE_HOURS,
    "body_weight_kg": WEIGHT_TOLERANCE_KG,
    "calories_estimate": 100,
    "protein_g_estimate": 10,
    "carbs_g_estimate": 15,
    "fat_g_estimate": 10,
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class CaseResult:
    """单个测试用例的评估结果"""
    test_id: str
    category: str
    evaluation_mode: str
    passed: bool
    partial: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """完整评估报告"""
    total_cases: int
    passed: int
    failed: int
    partial: int
    global_score: float
    by_capability: dict[str, dict]
    by_subcategory: dict[str, dict]
    error_distribution: dict[str, int]
    ece: float


# ---------------------------------------------------------------------------
# 字符串相似度辅助函数
# ---------------------------------------------------------------------------

def levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串之间的编辑距离"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def text_similarity(s1: str, s2: str) -> float:
    """基于编辑距离的文本相似度"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    max_len = max(len(s1), len(s2))
    return 1.0 - levenshtein_distance(s1, s2) / max_len


# ---------------------------------------------------------------------------
# 字段级比较
# ---------------------------------------------------------------------------

def compare_values(field_name: str, expected: Any, actual: Any) -> bool:
    """
    比较单个字段的值。

    返回 True 表示匹配，False 表示不匹配。
    """
    # 两端都为 None 视为匹配
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False

    # 精确匹配字段
    if field_name in EXACT_MATCH_FIELDS:
        return expected == actual

    # 数值容差匹配
    if field_name in NUMERIC_FIELDS:
        tolerance = NUMERIC_FIELDS[field_name]
        try:
            return abs(float(expected) - float(actual)) <= tolerance
        except (ValueError, TypeError):
            return expected == actual

    # 语义匹配：字符串相似度 >= 0.5
    if field_name in FUZZY_MATCH_FIELDS:
        return text_similarity(str(expected), str(actual)) >= 0.5

    # 默认精确匹配
    return expected == actual


def compare_fact_fields(expected_payload: dict, actual_payload: dict) -> tuple[int, int]:
    """
    比较两个 fact 的 normalized_payload 字段。

    返回 (matched_count, total_fields)。
    """
    total_fields = len(expected_payload)
    if total_fields == 0:
        return 0, 0

    matched = 0
    for field_name, expected_value in expected_payload.items():
        if field_name in actual_payload and compare_values(field_name, expected_value, actual_payload[field_name]):
            matched += 1

    return matched, total_fields


# ---------------------------------------------------------------------------
# 事实级匹配
# ---------------------------------------------------------------------------

def match_facts(
    expected_facts: list[dict],
    actual_facts: list[dict],
) -> dict[str, Any]:
    """
    将期望的事实与 Agent 输出的事实进行匹配。

    基于 fact_type 和 raw_text 的编辑距离进行贪心匹配。

    返回：
        {
            "tp": matched_pairs,
            "fp": unmatched_actual,
            "fn": unmatched_expected,
            "field_accuracy": matched_field_count / total_fields,
            "precision": ...,
            "recall": ...,
            "f1": ...
        }
    """
    if not expected_facts and not actual_facts:
        return {"tp": 0, "fp": 0, "fn": 0, "field_accuracy": 1.0,
                "precision": 1.0, "recall": 1.0, "f1": 1.0}

    # 构建距离矩阵
    unmatched_expected = list(range(len(expected_facts)))
    unmatched_actual = list(range(len(actual_facts)))
    matched_pairs = []
    total_matched_fields = 0
    total_expected_fields = 0

    # 贪心匹配：按距离升序配对
    while unmatched_expected and unmatched_actual:
        best_dist = float("inf")
        best_pair = None

        for ei in unmatched_expected:
            ef = expected_facts[ei]
            for ai in unmatched_actual:
                af = actual_facts[ai]
                # 基于 fact_type 和 raw_text 综合计算距离
                type_match = ef.get("fact_type") == af.get("fact_type")
                text_dist = levenshtein_distance(
                    ef.get("raw_text", ""), af.get("raw_text", "")
                )
                # 类型匹配的优先，然后在同类型内找最近文本
                total_dist = text_dist if type_match else text_dist + 1000
                if total_dist < best_dist:
                    best_dist = total_dist
                    best_pair = (ei, ai)

        if best_pair is None:
            break

        ei, ai = best_pair
        ef = expected_facts[ei]
        af = actual_facts[ai]

        matched, total = compare_fact_fields(
            ef.get("normalized_payload", {}),
            af.get("normalized_payload", {}),
        )
        total_matched_fields += matched
        total_expected_fields += total

        if ef.get("fact_type") == af.get("fact_type") and best_dist < 20:
            matched_pairs.append((ei, ai))

        unmatched_expected.remove(ei)
        unmatched_actual.remove(ai)

    tp = len(matched_pairs)
    fp = len(unmatched_actual)
    fn = len(unmatched_expected)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    field_acc = total_matched_fields / total_expected_fields if total_expected_fields > 0 else 1.0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "field_accuracy": field_acc,
        "precision": precision, "recall": recall, "f1": f1,
    }


# ---------------------------------------------------------------------------
# 意图分类
# ---------------------------------------------------------------------------

def evaluate_intent(actual: str, expected: str) -> bool:
    """评估单意图分类：精确匹配"""
    return actual == expected


def evaluate_intent_bundle(actual: list[str], expected: list[str]) -> dict:
    """评估多意图分解"""
    actual_set = set(actual)
    expected_set = set(expected)
    intersection = actual_set & expected_set
    precision = len(intersection) / len(actual_set) if actual_set else 0.0
    recall = len(intersection) / len(expected_set) if expected_set else 0.0
    return {"precision": precision, "recall": recall}


# ---------------------------------------------------------------------------
# 置信度校准
# ---------------------------------------------------------------------------

def compute_ece(predictions: list[dict]) -> float:
    """
    计算 Expected Calibration Error。

    predictions: 每个元素包含 {"confidence": float, "correct": bool}
    """
    if not predictions:
        return 0.0

    num_bins = 5
    bins = [[] for _ in range(num_bins)]

    for pred in predictions:
        conf = pred["confidence"]
        # 将置信度 0-1 映射到 0-4 的桶
        bin_idx = min(int(conf * num_bins), num_bins - 1)
        bins[bin_idx].append(pred)

    ece = 0.0
    n = len(predictions)
    for b in range(num_bins):
        if not bins[b]:
            continue
        bin_n = len(bins[b])
        bin_acc = sum(1 for p in bins[b] if p["correct"]) / bin_n
        bin_conf = sum(p["confidence"] for p in bins[b]) / bin_n
        ece += (bin_n / n) * abs(bin_acc - bin_conf)

    return ece


# ---------------------------------------------------------------------------
# 加载测试用例
# ---------------------------------------------------------------------------

def load_test_cases(filepath: str) -> list[dict]:
    """从 JSONL 文件加载测试用例"""
    cases = []
    with open(filepath, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                obj = json.loads(line)
                cases.append(obj)
            except json.JSONDecodeError as e:
                print(f"Warning: Line {line_no} in {filepath} is invalid JSON: {e}")
    return cases


# ---------------------------------------------------------------------------
# 单用例评估
# ---------------------------------------------------------------------------

def evaluate_case(case: dict, actual_output: dict) -> CaseResult:
    """
    评估单个测试用例。

    actual_output 的结构应与 expected 一致，即包含 intent_type / facts / memory_keys 等。
    """
    test_id = case["test_id"]
    category = case["category"]
    mode = case["evaluation_mode"]
    expected = case["expected"]
    result = CaseResult(test_id=test_id, category=category, evaluation_mode=mode)

    if category == "intent_classification":
        actual_intent = actual_output.get("intent_type", "")
        expected_intent = expected.get("intent_type", "")
        if mode == "exact":
            result.passed = actual_intent == expected_intent
        result.metrics["intent_accuracy"] = 1.0 if result.passed else 0.0

    elif category in ("multi_intent", "edge_case"):
        expected_bundle = expected.get("intent_bundle", [])
        actual_bundle = actual_output.get("intent_bundle", [])
        if expected_bundle:
            bundle_result = evaluate_intent_bundle(actual_bundle, expected_bundle)
            result.metrics.update(bundle_result)
            result.passed = bundle_result["recall"] >= 0.8
        if "facts" in expected:
            fact_result = match_facts(expected.get("facts", []), actual_output.get("facts", []))
            result.metrics.update(fact_result)
            if mode == "partial":
                result.passed = fact_result["fn"] == 0  # 期望的事实全部覆盖
            else:
                result.passed = result.passed and fact_result["f1"] >= 0.5

    elif category == "memory_extraction":
        expected_memories = expected.get("memory_keys", [])
        actual_memories = actual_output.get("memory_keys", [])
        if expected_memories:
            cat_correct = sum(
                1 for e in expected_memories
                if any(e["memory_category"] == a.get("memory_category") for a in actual_memories)
            )
            cat_acc = cat_correct / len(expected_memories)
            result.metrics["category_accuracy"] = cat_acc
            result.metrics["memory_score"] = cat_acc
            result.passed = cat_acc >= 0.8
        else:
            result.passed = len(actual_memories) == 0

    else:
        # Capabilities 2-5, 6: 事实提取
        expected_facts = expected.get("facts", [])
        actual_facts = actual_output.get("facts", [])

        if not expected_facts:
            result.passed = len(actual_facts) == 0
            return result

        fact_result = match_facts(expected_facts, actual_facts)
        result.metrics = fact_result

        if mode == "exact":
            result.passed = fact_result["fn"] == 0 and fact_result["fp"] == 0
        elif mode == "fuzzy":
            result.passed = fact_result["f1"] >= 0.75 and fact_result["field_accuracy"] >= 0.7
        elif mode == "partial":
            result.passed = fact_result["fn"] == 0

    return result


# ---------------------------------------------------------------------------
# 全量评估
# ---------------------------------------------------------------------------

def run_evaluation(test_files: list[str], get_actual_output) -> EvaluationReport:
    """
    运行全量评估。

    Args:
        test_files: JSONL 测试文件路径列表
        get_actual_output: 可调用对象，接受 test_case dict，返回 actual_output dict

    Returns:
        EvaluationReport
    """
    all_results = []
    all_cases = []

    for filepath in test_files:
        cases = load_test_cases(filepath)
        all_cases.extend(cases)

    for case in all_cases:
        actual = get_actual_output(case)
        result = evaluate_case(case, actual)
        all_results.append(result)

    # 汇总
    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed and not r.partial)
    partial = sum(1 for r in all_results if r.partial)
    failed = total - passed - partial

    # 按能力汇总
    by_capability = {}
    for r in all_results:
        cap = r.category
        if cap not in by_capability:
            by_capability[cap] = {"passed": 0, "total": 0}
        by_capability[cap]["total"] += 1
        if r.passed and not r.partial:
            by_capability[cap]["passed"] += 1
    for cap, stats in by_capability.items():
        stats["accuracy"] = stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0

    # 按场景汇总
    by_subcategory = {}
    for case in all_cases:
        sub = case.get("subcategory", "unknown")
        if sub not in by_subcategory:
            by_subcategory[sub] = {"cases": 0}
        by_subcategory[sub]["cases"] += 1

    # 全局评分（简化版）
    global_score = passed / total if total > 0 else 0.0

    return EvaluationReport(
        total_cases=total,
        passed=passed,
        failed=failed,
        partial=partial,
        global_score=global_score,
        by_capability=by_capability,
        by_subcategory=by_subcategory,
        error_distribution={},
        ece=0.0,
    )
