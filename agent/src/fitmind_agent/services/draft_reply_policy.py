"""Conservative interpretation of replies to a pending business draft."""

import re
from typing import Literal


def classify_draft_reply(message: str) -> Literal["confirm", "cancel", "question", "revise"]:
    normalized = re.sub(r"[\s，。！!、,]", "", message.lower())
    # Corrections take precedence even when phrased as polite questions.
    correction_words = ("修改", "改成", "改为", "换成", "纠正", "不是", "应该", "补充", "调整")
    if any(word in normalized for word in correction_words):
        return "revise"
    if normalized in {
        "取消", "取消保存", "不要", "不要保存", "作废", "先不", "不保存", "先不保存", "算了", "放弃",
    }:
        return "cancel"
    if any(word in normalized for word in ("为什么", "怎么", "什么意思", "哪里", "吗", "？", "?")):
        return "question"
    if normalized in {
        "确认", "确认保存", "确认落库", "可以", "可以保存", "没问题", "保存", "落库",
        "对的", "没错", "好的", "好的保存", "好的确认保存", "确认无误", "确认保存吧",
    }:
        return "confirm"
    return "revise"
