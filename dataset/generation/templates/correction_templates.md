# 纠错场景模板

> 纠错理解（Capability 6）的变量模板。

---

## 1. 纠错类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 重量纠错 | 修改动作重量 | "卧推改成55kg" |
| 组次纠错 | 修改组数或次数 | "深蹲是3组不是4组" |
| 动作纠错 | 修改动作名称 | "不是杠铃划船，是哑铃划船" |
| 主题纠错 | 修改训练主题 | "不是练胸，是练背" |
| 补充遗漏 | 补加之前没说的内容 | "刚才忘说了，还做了拉伸" |
| 删除记录 | 删除之前记录 | "把刚才的记录删了" |
| 全部重来 | 清空重记 | "全删了重新来" |

---

## 2. 重量纠错模板

```python
weight_correction_templates = [
    "把刚才的{exercise}改成{new_weight}kg",
    "刚才说的{exercise}不是{old_weight}kg，是{new_weight}kg",
    "{exercise}纠正一下，应该是{new_weight}kg",
    "{exercise}说错了，{new_weight}kg才对",
    "不对，{exercise}是{new_weight}不是{old_weight}",
    "那个{exercise}的重量改一下，改成{new_weight}",
    "{exercise}的重量我记错了，应该是{new_weight}",
]
```

---

## 3. 组次纠错模板

```python
reps_correction_templates = [
    "{exercise}是{sets}组{reps}次，不是{old_sets}组{old_reps}次",
    "{exercise}少说了一组，应该{total_sets}组",
    "{exercise}的组次数改成{sets}x{reps}",
    "{exercise}最后一组没做，只做了{completed_sets}组",
]
```

---

## 4. 动作纠错模板

```python
exercise_correction_templates = [
    "不是{old_exercise}，是{new_exercise}",
    "{old_exercise}说错了，其实做的是{new_exercise}",
    "那个动作我记混了，是{new_exercise}不是{old_exercise}",
    "{old_exercise}换成{new_exercise}",
]
```

---

## 5. 补充遗漏模板

```python
supplement_templates = [
    "刚才忘说了，还做了{exercise}{details}",
    "对了，还练了{exercise}，{details}",
    "补充一下，练完之后{activity}了{minutes}分钟",
    "差点忘了，{exercise}{details}",
    "哦还有{exercise}也做了",
]
```

---

## 6. 删除/清空模板

```python
delete_templates = [
    "把刚才的记录删了",
    "刚才那条删掉",
    "那条记录不对，删了重来",
    "全删了重新记录",
    "清空今天的所有记录",
    "刚才的全部撤销",
]
```

---

## 7. 模糊指代模板

```python
# 依赖上下文解析
vague_reference_templates = [
    "改成这个重量",           # 无明确目标
    "那个动作的重量改一下",    # 目标模糊
    "刚才那个不对",            # 无明确目标和值
    "换一个",                 # 极度模糊
    "和昨天一样",             # 依赖历史
]
```

---

## 8. 边界场景

### 8.1 应该触发确认门控

```
"把所有的全删了"           → 高风险批量操作，必须确认
"那个改成50"               → 目标不明，应该追问
"刚才说的几个都改一下"      → 多目标不确定
```

### 8.2 一次性纠正多个

```
"卧推改成55，深蹲改成90，硬拉去掉了没做"
```
应在一条消息中识别出 3 个独立的纠正操作。

---

## 9. 期望输出示例

### 9.1 重量纠错

```json
{
  "test_id": "COR-XXX",
  "category": "correction",
  "subcategory": "happy_path",
  "input": "把刚才的卧推改成55kg",
  "expected": {
    "facts": [
      {
        "fact_type": "correction",
        "raw_text": "卧推改成55kg",
        "normalized_payload": {
          "target_exercise": "卧推",
          "field_to_change": "weight_kg",
          "new_value": 55,
          "reason": "weight_correction"
        }
      }
    ]
  },
  "evaluation_mode": "fuzzy",
  "tags": ["weight_correction", "simple"]
}
```

### 9.2 补充遗漏

```json
{
  "test_id": "COR-XXX",
  "category": "correction",
  "subcategory": "edge_case",
  "input": "刚才忘说了，练完还做了10分钟拉伸",
  "expected": {
    "facts": [
      {
        "fact_type": "supplement",
        "raw_text": "10分钟拉伸",
        "normalized_payload": {
          "exercise_name": "拉伸",
          "duration_minutes": 10,
          "reason": "supplement_to_previous_record"
        }
      }
    ]
  },
  "evaluation_mode": "fuzzy",
  "tags": ["supplement", "addendum"]
}
```
