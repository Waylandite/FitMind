# 测试用例生成策略

> 本文档定义如何系统化、规模化地生成 FitMind Agent 的批量测试用例。

---

## 1. 生成策略概览

| 策略 | 适用能力 | 预期产出 | 难度 |
|------|---------|---------|------|
| 模板组合生成 | C-02, C-03, C-04, C-05 | 数千条用例 | 低 |
| 同义词/变体扩展 | 全部 | 从现有用例扩增 5-10 倍 | 低 |
| 对抗样本设计 | 全部 | 100+ 挑战性用例 | 高 |
| 数据增强 | 全部 | 对现有用例注入噪声和变体 | 中 |
| 人工标注补充 | C-01, C-06, C-08 | 人工标注的高质量 gold 集 | 高 |

---

## 2. 模板组合生成

### 2.1 原理

将每个测试领域分解为独立的变量维度，通过笛卡尔积组合生成大量测试用例。

### 2.2 训练记录生成

**变量维度**：

```
训练部位: [胸, 背, 腿, 肩, 手臂, 全身, 有氧]
动作词表: 50+ 个动作（见 templates/workout_templates.md）
重量列表: [20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140] 单位 kg
组次模式: ["3x8", "3x10", "3x12", "4x8", "4x10", "4x12", "5x5", "3x5", "4x6"]
完成状态: ["全部完成", "基本完成", "前两组完成第三组没做完", "最后一组力竭没完成", "减重完成"]
主观强度: [5, 6, 7, 8, 9]
精神状态: ["状态好", "状态一般", "有点累", "很精神", "还行"]
时间前缀: ["今天", "昨天", "周一", "周二"]
```

**组合公式**：

```
模板: "{时间}练{部位}, {动作1}{重量}kg {组次}, {动作2}{重量}kg {组次}, 感觉{强度}, {精神}"

预估数量: 7(部位) × 50×49/2(动作组合) × 6(组次) × 5(状态) × 9(强度) × 5(精神)
         ≈ 2.3 亿 组合 (全组合)
```

**实用采样**：随机采样 500 个组合 + 20 个手工精选代表组合。

### 2.3 饮食记录生成

**变量维度**：

```
餐次: [早餐, 午餐, 晚餐, 加餐]
食物词表: 30+ 食物（见 templates/nutrition_templates.md）
补剂词表: 10 种常见补剂
时间: [早上, 中午, 下午, 晚上, 训练前, 训练后]
```

**组合公式**：

```
模板 1: "{时间}吃了{餐次}: {食物1}, {食物2}, {食物3}"
模板 2: "训练{前后}喝了{补剂}"
```

预估数量：相对可控，约 100-200 条精选用例。

### 2.4 身体状态生成

**变量维度**：

```
睡眠时长: [4, 5, 6, 6.5, 7, 7.5, 8, 8.5, 9]
疲劳度: [3, 4, 5, 6, 7, 8, 9]
压力: [2, 3, 4, 5, 6, 7, 8, 9]
酸痛部位: [腿, 背, 肩, 胸, 手臂, 全身, 无]
体重: [60, 65, 70, 75, 80, 85, 90] 单位 kg
情绪: ["还不错", "一般", "很好", "有点差", "比较累"]
```

**组合公式**：

```
模板: "昨晚睡了{睡眠}h, 今天疲劳感{疲劳}, 压力{压力}, {部位}{有无}酸, 体重{体重}kg, 精神状态{情绪}"
```

---

## 3. 同义词与变体扩展

### 3.1 扩展策略

对每条现有测试用例，通过替换关键词生成变体：

1. 动作名变体：`卧推` → `杠铃卧推` / `bench press` / `平板卧推`
2. 意图关键词变体：详见 `augmentation/synonym_map.md`
3. 量词变体：`60kg` → `60公斤` / `六十公斤` / `120斤` / `60 kilo`
4. 时间变体：`今天` → `昨天` / `周一` / `2026-06-11`
5. 顺序变体：重排消息中的事实顺序

### 3.2 扩增率

一条基础用例 → 3-5 条变体用例。

49 条现有用例 → 约 150-250 条扩增用例。

---

## 4. 对抗样本设计

### 4.1 目标

构造专门挑战系统的输入，测试鲁棒性边界。

### 4.2 对抗模式

详见 `augmentation/adversarial_patterns.md`。

主要模式：
- **否定嵌入**："没做卧推，做了哑铃推举"（关键词"卧推"出现但不相关）
- **跨领域关键词**："吃了蛋白粉之后训练"（"吃"出现在训练语境中）
- **自纠错**："卧推60kg...不对，其实是55kg"
- **中英混合**："bench press 185lbs 5x5, lateral raise 25lbs 4x12"
- **英制单位**：lbs 转 kg
- **模糊指代**："和昨天一样"、"像上次那样"
- **反问句**："你觉得我今天练了吗？"
- **极度口语**："干就完了，今天怼了胸，爽"

---

## 5. 数据增强

### 5.1 噪声注入

在消息前后添加无意义填充词，不改变语义：

```
原文: "今天练胸，卧推60kg 5x5"
增强: "嗯今天练胸，然后做了卧推60kg 5x5，就这样"
```

### 5.2 语序扰动

保持事实不变，改变消息中事实的出现顺序：

```
原文: "深蹲80kg，腿举120kg，状态还行"
增强: "状态还行，腿举120kg，深蹲80kg"
```

### 5.3 句式变换

```
陈述句: "今天练了胸"
疑问句: "今天练胸了"
口语化: "胸，今天搞了"
```

---

## 6. 自动化生成脚本设计

未来的自动化生成脚本 `generate_test_cases.py` 的结构：

```python
class TestCaseGenerator:
    def __init__(self, templates_dir: str, augmentation_dir: str):
        self.templates = load_templates(templates_dir)
        self.synonyms = load_synonym_map(augmentation_dir)

    def generate_workout_cases(self, count: int) -> list[dict]:
        """组合式生成训练用例"""
        cases = []
        for _ in range(count):
            exercise = random.choice(self.templates["exercises"])
            weight = random.choice(self.templates["weights"])
            sr = random.choice(self.templates["sets_reps"])
            body_part = random.choice(self.templates["body_parts"])
            # ... build input and expected ...
        return cases

    def expand_with_synonyms(self, cases: list[dict]) -> list[dict]:
        """同义词扩展"""
        expanded = []
        for case in cases:
            for variant in generate_variants(case, self.synonyms):
                expanded.append(variant)
        return expanded

    def inject_noise(self, cases: list[dict]) -> list[dict]:
        """噪声注入"""
        # ...

    def save(self, cases: list[dict], filepath: str):
        """保存为 JSONL"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for case in cases:
                f.write(json.dumps(case, ensure_ascii=False) + '\n')
```

---

## 7. 测试集分层

建议将测试集分为三层：

| 层级 | 规模 | 用途 | 用例来源 |
|------|------|------|---------|
| **Smoke Test** | 10 条 | CI/CD 快速验证，每次提交运行 | 手工精选关键路径用例 |
| **Standard Test** | 100 条 | 每日构建测试 | Smoke + 同义词扩展 |
| **Full Test** | 500+ 条 | 发布前全面评估 | 全部生成策略组合 |

---

## 8. 质量保障

### 8.1 期望输出校验

每条生成的测试用例的 `expected` 必须：
1. 通过 `schemas/test_case_schema.json` 的 schema 验证
2. 各字段值符合 DB CHECK 约束
3. `raw_text` 必须是 `input` 的子串

### 8.2 覆盖率检查

确保测试集覆盖：
- 全部 8 种意图类型
- 全部 13 种 fact_type
- 全部 5 种 workout completion_status 枚举值
- 全部 13 种 memory_category 枚举值
- 1-10 范围的 exertion 极值（1, 10）
- 中英混合输入
- 空输入、超长输入

### 8.3 定期评审

- 每轮 Agent 更新后，重新运行测试
- 失败的用例：分析根因（模型退化 vs 期望过时 vs 新增 bug）
- 持续补充新的对抗样本和边界用例
