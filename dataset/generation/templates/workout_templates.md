# 训练相关模板

> 训练计划提取（Capability 2）和训练结果提取（Capability 3）的变量模板。

---

## 1. 动作词表

### 1.1 胸部动作

```
卧推, 杠铃卧推, 哑铃卧推, 上斜卧推, 上斜哑铃推举, 下斜卧推,
哑铃飞鸟, 绳索夹胸, 蝴蝶机夹胸, 双杠臂屈伸, 俯卧撑, 窄距卧推
```

### 1.2 背部动作

```
引体向上, 高位下拉, 杠铃划船, 哑铃划船, 坐姿划船, T杠划船,
面拉, 直臂下拉, 硬拉, 罗马尼亚硬拉, 山羊挺身, 俯身飞鸟
```

### 1.3 腿部动作

```
深蹲, 杠铃深蹲, 前蹲, 保加利亚分腿蹲, 哈克深蹲, 倒蹬, 腿举,
腿弯举, 腿屈伸, 箭步蹲, 提踵, 站姿提踵, 坐姿提踵,
臀推, 髋外展, 髋内收
```

### 1.4 肩部动作

```
杠铃推举, 哑铃推举, 阿诺德推举, 侧平举, 前平举, 俯身侧平举,
面拉, 直立划船, 杠铃耸肩, 哑铃耸肩
```

### 1.5 手臂动作

```
杠铃弯举, 哑铃弯举, 锤式弯举, 牧师凳弯举, 集中弯举,
仰卧臂屈伸, 绳索下压, 窄距卧推, 单臂臂屈伸, 杠铃臂屈伸
```

### 1.6 核心动作

```
卷腹, 平板支撑, 悬垂举腿, 俄罗斯转体, 山羊挺身,
仰卧起坐, 侧平板, V字卷腹, 绳索卷腹, 死虫
```

### 1.7 有氧/体能

```
跑步, 椭圆机, 动感单车, 游泳, 跳绳, 划船机,
爬楼梯, 快走, 间歇跑, HIIT, 战绳, 波比跳
```

---

## 2. 重量列表

常用重量档位（单位 kg）：

```python
weights = [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 110, 120, 140, 160]
```

哑铃常用重量（单只）：

```python
dumbbell_weights = [5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30, 35, 40]
```

自体重动作不计重量。

---

## 3. 组次模式

```python
sets_reps_patterns = [
    {"sets": 3, "reps": 5,  "text": "3x5"},
    {"sets": 3, "reps": 8,  "text": "3x8"},
    {"sets": 3, "reps": 10, "text": "3x10"},
    {"sets": 3, "reps": 12, "text": "3x12"},
    {"sets": 3, "reps": 15, "text": "3x15"},
    {"sets": 4, "reps": 6,  "text": "4x6"},
    {"sets": 4, "reps": 8,  "text": "4x8"},
    {"sets": 4, "reps": 10, "text": "4x10"},
    {"sets": 4, "reps": 12, "text": "4x12"},
    {"sets": 5, "reps": 5,  "text": "5x5"},
    {"sets": 5, "reps": 10, "text": "5x10"},
]
```

---

## 4. 完成状态描述

```python
completion_statuses = [
    {"status": "completed", "text": "全部完成"},
    {"status": "completed", "text": "做完了"},
    {"status": "completed", "text": "顺利完成"},
    {"status": "completed", "text": "完成了"},
    {"status": "partial", "text": "最后一组没做完"},
    {"status": "partial", "text": "第3组只做了8个"},
    {"status": "partial", "text": "减重完成了"},
    {"status": "partial", "text": "最后两组没做"},
    {"status": "partial", "text": "只做了前面几组"},
    {"status": "skipped", "text": "没练"},
    {"status": "skipped", "text": "休息日"},
    {"status": "skipped", "text": "今天休息"},
    {"status": "skipped", "text": "没去健身房"},
]
```

---

## 5. 主观强度与精神状态

### 5.1 主观强度（RPE 1-10）

```python
exertion_levels = {
    5:  ["强度5", "感觉5分", "强度大概5", "练得一般"],
    6:  ["强度6", "感觉6分", "还行"],
    7:  ["强度7", "感觉7分", "练得还可以", "状态不错"],
    8:  ["强度8", "感觉8分", "练得挺累的", "强度挺大"],
    9:  ["强度9", "感觉9分", "练得很累", "差点力竭"],
    10: ["强度10", "感觉10分", "完全力竭", "练到极限了"],
}
```

### 5.2 精神状态

```python
mood_values = [
    "状态好", "状态不错", "状态很好", "状态一般",
    "有点累", "精神很好", "很精神", "还行", "比较疲惫",
    "精神一般", "心情好", "情绪稳定",
]
```

---

## 6. 有氧项目模板

```python
cardio_templates = [
    {"exercise": "跑步", "patterns": ["跑步{min}分钟", "跑了{min}分钟", "跑步{dist}公里"]},
    {"exercise": "椭圆机", "patterns": ["椭圆机{min}分钟"]},
    {"exercise": "动感单车", "patterns": ["动感单车{min}分钟", "单车{min}分钟"]},
    {"exercise": "游泳", "patterns": ["游泳{dist}米", "游了{dist}米"]},
    {"exercise": "跳绳", "patterns": ["跳绳{min}分钟", "跳了{cnt}个"]},
    {"exercise": "划船机", "patterns": ["划船机{min}分钟", "划了{dist}米"]},
]

# 变量值范围
cardio_values = {
    "min": [10, 15, 20, 25, 30, 40, 45, 60],
    "dist": [1, 2, 3, 5, 8, 10],
    "cnt": [500, 1000, 2000],
}
```

---

## 7. 消息模板

### 7.1 简单单动作

```
"{时间}练{部位}, {动作}{重量}kg {组次}"
```

### 7.2 多动作 + 状态

```
"{时间}练{部位}, {动作1}{重量1}kg {组次1}, {动作2}{重量2}kg {组次2}, {动作3}{组次3}, 感觉{强度}, {精神}"
```

### 7.3 有氧 + 力量

```
"{时间}练{部位}: {力量动作1}, {力量动作2}。然后跑了{有氧}分钟{有氧项目}。感觉{强度}。"
```

### 7.4 部分完成

```
"{时间}练{部位}, {动作} {完成描述}。总体感觉{强度}。"
```

---

## 8. 生成算法伪代码

```python
def generate_workout_case():
    body_part = random.choice(body_parts)
    exercises = random.sample(BY_PART[body_part], k=random.randint(1, 4))
    time = random.choice(["今天", "昨天", "周一", "周二", "周三"])
    exertion = random.choice(list(exertion_levels.keys()))
    mood = random.choice(mood_values)
    completion = random.choice(completion_statuses)

    # 构建消息
    parts = [f"{time}练{body_part}"]
    for ex in exercises:
        weight = random.choice(weights)
        sr = random.choice(sets_reps_patterns)
        parts.append(f"{ex}{weight}kg {sr['text']}")
    parts.append(f"感觉{exertion}")
    parts.append(f"{mood}")

    input_text = "，".join(parts)

    # 构建期望输出
    expected = {
        "facts": []
    }
    for ex in exercises:
        expected["facts"].append({
            "fact_type": "completed_exercise",
            "raw_text": f"{ex}{weight}kg {sr['text']}",
            "normalized_payload": {
                "exercise_name": ex,
                "weight_kg": weight,
                "sets": sr["sets"],
                "reps": sr["reps"],
                "completed": True
            },
            "confidence": 0.9
        })
    # ... add exertion, mood, completion_status facts

    return {
        "test_id": f"WOR-{next_id()}",
        "category": "workout_result",
        "subcategory": "happy_path",
        "input": input_text,
        "expected": expected,
        "evaluation_mode": "fuzzy",
        "tags": [body_part, "generated"]
    }
```
