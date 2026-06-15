# 饮食相关模板

> 饮食提取（Capability 5）的变量模板。包含食物词表、餐次结构、补剂词表。

---

## 1. 食物词表

### 1.1 蛋白质来源

```
鸡胸肉, 鸡腿, 鸡翅, 鸡蛋, 蛋白, 牛肉, 牛排, 猪肉, 猪排,
三文鱼, 金枪鱼, 虾, 鱼片, 豆腐, 豆浆, 牛奶, 酸奶, 奶酪,
蛋白粉, 火鸡胸, 鸭胸, 羊排
```

### 1.2 碳水化合物来源

```
米饭, 糙米饭, 燕麦, 全麦面包, 面包, 面条, 意大利面, 红薯,
土豆, 玉米, 馒头, 包子, 饺子, 年糕, 米粉, 面包片, 藜麦,
香蕉, 苹果, 橘子
```

### 1.3 蔬菜

```
西兰花, 菠菜, 生菜, 番茄, 黄瓜, 胡萝卜, 青椒, 茄子,
蘑菇, 洋葱, 芦笋, 花菜, 芹菜, 沙拉, 卷心菜
```

### 1.4 外食/其他

```
火锅, 烧烤, 寿司, 拉面, 汉堡, 披萨, 沙拉碗, 三明治,
麦当劳, 巨无霸, 盒饭, 麻辣烫
```

### 1.5 饮品

```
牛奶, 豆浆, 蛋白粉, 果汁, 咖啡, 绿茶, 酸奶
```

---

## 2. 补剂词表

```python
supplements = {
    "蛋白粉": {"timing": ["训练后", "早上", "晚上", "两餐之间"], "protein_g": 25},
    "BCAA":  {"timing": ["训练前", "训练中", "早上"], "protein_g": 0},
    "肌酸":  {"timing": ["训练后", "训练前", "早上"], "protein_g": 0},
    "氮泵":  {"timing": ["训练前"], "protein_g": 0},
    "谷氨酰胺": {"timing": ["训练后", "睡前"], "protein_g": 0},
    "左旋肉碱":  {"timing": ["训练前", "早上"], "protein_g": 0},
    "鱼油":  {"timing": ["饭后", "早上"], "protein_g": 0},
    "维生素": {"timing": ["早上", "饭后"], "protein_g": 0},
    "ZMA":   {"timing": ["睡前"], "protein_g": 0},
    "增肌粉": {"timing": ["训练后"], "protein_g": 30},
}
```

---

## 3. 餐次结构

```python
meal_structures = {
    "早餐": {
        "foods": [["鸡蛋", "燕麦", "牛奶"], ["全麦面包", "鸡蛋", "豆浆"], ["燕麦", "蛋白粉", "香蕉"]],
        "timing": ["早上", "早餐", "早上7点", "8点吃的早饭", "早晨"],
        "protein_range": (20, 35),
        "carbs_range": (40, 60),
        "fat_range": (10, 20),
    },
    "午餐": {
        "foods": [["鸡胸肉", "米饭", "西兰花"], ["牛肉", "面条", "青菜"], ["三文鱼", "糙米饭", "沙拉"]],
        "timing": ["中午", "午餐", "中午12点", "午饭"],
        "protein_range": (35, 55),
        "carbs_range": (60, 90),
        "fat_range": (10, 25),
    },
    "晚餐": {
        "foods": [["牛排", "土豆", "菠菜"], ["鸡胸肉", "红薯", "西兰花"], ["鱼", "米饭", "蔬菜"]],
        "timing": ["晚上", "晚餐", "晚上7点", "晚饭"],
        "protein_range": (30, 50),
        "carbs_range": (30, 60),
        "fat_range": (10, 20),
    },
    "加餐": {
        "foods": [["蛋白粉", "香蕉"], ["酸奶", "坚果"], ["鸡蛋"], ["蛋白棒"]],
        "timing": ["下午", "训练后", "加餐"],
        "protein_range": (10, 30),
        "carbs_range": (10, 30),
        "fat_range": (5, 15),
    },
}
```

---

## 4. 份量描述

```python
portion_descriptions = [
    "一碗", "一盘", "一份", "半碗", "200g", "150g", "300g",
    "一个", "两个", "三片", "一把", "两勺", "一小块", "一块",
    "一大碗", "半块", "适量", "不少", "挺多的",
]
```

---

## 5. 消息模板

### 5.1 完整一日三餐

```
"今天{早餐时间}{早餐食物}。{午餐时间}{午餐食物}。{晚餐时间}{晚餐食物}。{补剂时间}喝了{补剂}。"
```

### 5.2 单餐

```
"{时间}吃了{食物1}和{食物2}"
```

### 5.3 模糊描述

```
"今天吃了三顿，正常饮食"
"饮食跟昨天差不多"
"今天没怎么吃"
"今天吃多了"
"今天只吃了一顿"
```

### 5.4 补剂专用

```
"训练后喝了一勺{蛋白粉}"
"早上{BCAA}, 训练前{氮泵}, 训练后{蛋白粉}+{肌酸}"
```

---

## 6. 生成示例

```python
def generate_nutrition_case(meal_count: int = 3):
    meals = []
    facts = []
    selected_meals = random.sample(list(meal_structures.keys()), k=min(meal_count, len(meal_structures)))

    for meal_type in selected_meals:
        structure = meal_structures[meal_type]
        foods = random.choice(structure["foods"])
        timing = random.choice(structure["timing"])
        meals.append(f"{timing}{'，'.join(foods)}")
        facts.append({
            "fact_type": "meal",
            "raw_text": f"{timing}{'，'.join(foods)}",
            "normalized_payload": {
                "meal_type": meal_type,
                "foods": foods,
            }
        })

    # 随机加补剂
    if random.random() > 0.5:
        supp = random.choice(list(supplements.keys()))
        timing = random.choice(supplements[supp]["timing"])
        meals.append(f"{timing}喝了{supp}")
        facts.append({
            "fact_type": "supplement",
            "raw_text": f"{timing}喝了{supp}",
            "normalized_payload": {
                "supplement_name": supp,
                "timing": timing,
            }
        })

    input_text = "。".join(meals) + "。"

    return {
        "test_id": f"NUT-{next_id()}",
        "category": "nutrition",
        "subcategory": "happy_path",
        "input": input_text,
        "expected": {"facts": facts},
        "evaluation_mode": "fuzzy",
        "tags": ["generated", f"{meal_count}_meals"]
    }
```
