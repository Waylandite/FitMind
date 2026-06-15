# JSONL 文件格式规范

## 1. 基本规则

1. **每行一个 JSON 对象**：每行包含一个完整的、自描述的 JSON 对象
2. **UTF-8 编码**：无 BOM（Byte Order Mark）
3. **紧凑格式**：每条记录在一行内（不超过 4096 字符推荐上限）
4. **无尾随逗号**：每行是独立的合法 JSON
5. **换行符**：`\n` (LF)，不使用 `\r\n` (CRLF)

## 2. 注释

以 `//` 开头的行视为注释：

```jsonl
// 这是注释行，测试运行器应自动忽略
// 用于文件级说明、分组标注等

{"test_id":"INT-001","category":"intent_classification","subcategory":"happy_path","input":"今天练胸","expected":{"intent_type":"workout"},"evaluation_mode":"exact","tags":["simple"]}
```

## 3. 空行

空白行自动忽略。可以用于视觉分组：

```jsonl
// === 单意图测试 ===

{"test_id":"INT-001",...}

{"test_id":"INT-002",...}

// === 边界用例 ===

{"test_id":"INT-007",...}
```

## 4. JSON 格式要求

### 4.1 字符串

- 必须使用双引号 `"`
- 中文文本直接写入，不转义
- 特殊字符（如 `"`, `\`, 换行符）需转义

**正确**：
```json
{"input": "今天练胸，卧推60kg 5x5"}
```

**错误**：
```json
{'input': '今天练胸，卧推60kg 5x5'}
```

### 4.2 数值

- 整数：不带小数点
- 浮点数：使用小数点
- 避免科学计数法

```json
{"weight_kg": 60, "sleep_hours": 7.5, "confidence": 0.95}
```

### 4.3 布尔值

- 小写：`true` / `false`

### 4.4 null

- 小写：`null`

## 5. Schema 验证

所有 JSONL 文件中的每条记录必须通过 `schemas/test_case_schema.json` 的验证。

验证脚本示例：

```python
import json
import jsonschema

def validate_jsonl(filepath: str, schema_path: str) -> bool:
    with open(schema_path) as f:
        schema = json.load(f)
    with open(filepath) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            try:
                obj = json.loads(line)
                jsonschema.validate(obj, schema)
            except json.JSONDecodeError as e:
                print(f"Line {line_no}: Invalid JSON - {e}")
                return False
            except jsonschema.ValidationError as e:
                print(f"Line {line_no}: Schema validation failed - {e.message}")
                return False
    return True
```

## 6. 文件命名规范

- 文件名：`{category}.jsonl`
- 所有测试用例文件放在 `test_cases/` 目录下
- 文件名反映测试能力类别

## 7. 字段顺序

JSON 对象内字段顺序不严格要求，但建议保持一致性以增强可读性。推荐顺序：

```json
{
  "test_id": "...",
  "category": "...",
  "subcategory": "...",
  "input": "...",
  "expected": {...},
  "evaluation_mode": "...",
  "notes": "...",
  "tags": [...]
}
```

## 8. 行长度

推荐每行不超过 4096 字符。对于复杂的 `expected` 对象，如果超过限制：

- 在 JSON 内使用适当的缩进（仍然在一行内）
- 或将超长字段拆分为多个独立的测试用例

## 9. 示例文件结构

```
dataset/test_cases/intent_classification.jsonl

行 1: // FitMind Agent 意图分类测试用例
行 2: // 测试能力: C-01 意图路由
行 3:
行 4: {"test_id":"INT-001",...,"evaluation_mode":"exact","tags":["single_intent"]}
行 5: {"test_id":"INT-002",...,"evaluation_mode":"exact","tags":["single_intent"]}
...
```
