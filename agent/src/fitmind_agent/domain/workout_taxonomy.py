from fitmind_agent.schemas.workout_history import MuscleGroup


MUSCLE_GROUP_LABELS: dict[MuscleGroup, str] = {
    "chest": "胸",
    "back": "背",
    "legs": "腿",
    "shoulders": "肩",
    "arms": "手臂",
    "core": "核心",
    "full_body": "全身",
    "cardio": "有氧",
    "other": "其他",
}

MUSCLE_GROUP_ALIASES: dict[MuscleGroup, tuple[str, ...]] = {
    "chest": ("胸", "卧推", "飞鸟", "夹胸", "俯卧撑", "双杠臂屈伸"),
    "back": ("背", "引体", "下拉", "划船", "直臂下压"),
    "legs": ("腿", "深蹲", "腿举", "箭步", "臀桥", "臀推", "腿屈伸", "腿弯举", "提踵"),
    "shoulders": ("肩", "肩推", "推举", "侧平举", "前平举", "面拉"),
    "arms": ("手臂", "二头", "三头", "弯举", "臂屈伸"),
    "core": ("核心", "卷腹", "平板", "俄罗斯转体", "死虫"),
    "full_body": ("全身", "波比", "壶铃摆动", "农夫行走"),
    "cardio": ("有氧", "跑步", "慢跑", "快走", "骑行", "单车", "游泳", "跳绳", "椭圆"),
    "other": (),
}

COMPOSITE_EXERCISE_GROUPS: dict[str, tuple[MuscleGroup, ...]] = {
    "硬拉": ("legs", "back"),
    "高翻": ("legs", "back", "shoulders"),
}


def resolve_muscle_groups(text: str, *, exercise_type: str | None = None) -> list[MuscleGroup]:
    normalized = text.lower()
    groups: list[MuscleGroup] = []
    for phrase, mapped_groups in COMPOSITE_EXERCISE_GROUPS.items():
        if phrase in normalized:
            groups.extend(mapped_groups)
    for group, aliases in MUSCLE_GROUP_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            groups.append(group)
    if exercise_type == "cardio":
        groups.append("cardio")
    return list(dict.fromkeys(groups)) or ["other"]
