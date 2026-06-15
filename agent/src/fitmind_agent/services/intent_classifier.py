from __future__ import annotations

import json
import re

from fitmind_agent.schemas.intent import IntentCode
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.intent import KeywordIntentMatch
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


INTENT_KEYWORDS: dict[IntentCode, tuple[str, ...]] = {
    "today_workout_record": (
        "今天练",
        "今天训练",
        "练了",
        "做了",
        "完成了",
        "卧推",
        "深蹲",
        "硬拉",
        "组",
        "次数",
        "kg",
        "公斤",
    ),
    "recent_workout_summary": (
        "最近",
        "这几天",
        "这周",
        "本周",
        "总结",
        "回顾",
        "分析一下",
        "训练情况",
    ),
    "today_workout_recommendation": (
        "今天练什么",
        "推荐训练",
        "安排今天",
        "帮我安排",
        "训练计划推荐",
        "怎么练",
        "练哪里",
    ),
    "today_nutrition_record": (
        "吃了",
        "喝了",
        "饮食",
        "早餐",
        "午餐",
        "晚餐",
        "加餐",
        "蛋白",
        "碳水",
        "脂肪",
        "热量",
        "卡路里",
        "千卡",
        "kcal",
    ),
    "today_body_status_record": (
        "睡了",
        "睡眠",
        "起床",
        "困",
        "疲劳",
        "酸痛",
        "恢复",
        "体重",
        "状态",
        "压力",
        "精神",
        "心情",
    ),
    "user_workout_plan_update": (
        "更新计划",
        "修改计划",
        "调整计划",
        "长期计划",
        "周计划",
        "阶段计划",
        "增肌计划",
        "减脂计划",
        "目标",
    ),
}

VALID_INTENTS: set[IntentCode] = {
    "today_workout_record",
    "recent_workout_summary",
    "today_workout_recommendation",
    "today_nutrition_record",
    "today_body_status_record",
    "user_workout_plan_update",
    "general_chat",
    "unknown",
}


class IntentClassifier:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
        confidence_threshold: float = 0.7,
        keyword_threshold: float = 0.55,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.confidence_threshold = confidence_threshold
        self.keyword_threshold = keyword_threshold

    def classify(self, user_query: str) -> IntentRecognitionResult:
        keyword_match = self.classify_by_keywords(user_query)
        llm_result = self._classify_by_llm(user_query=user_query, keyword_match=keyword_match)

        if llm_result and llm_result.confidence >= self.confidence_threshold:
            return llm_result

        if keyword_match and keyword_match.confidence >= self.keyword_threshold:
            return IntentRecognitionResult(
                intent=keyword_match.intent,
                confidence=keyword_match.confidence,
                source="keyword",
                reason="关键词规则命中，模型置信度不足或模型识别失败。",
                keyword_match=keyword_match,
            )

        return IntentRecognitionResult(
            intent=llm_result.intent if llm_result else "unknown",
            confidence=llm_result.confidence if llm_result else 0.0,
            source="fallback",
            reason=llm_result.reason if llm_result else "未获得稳定意图。",
            keyword_match=keyword_match,
        )

    def classify_by_keywords(self, user_query: str) -> KeywordIntentMatch | None:
        normalized = user_query.lower().strip()
        scored_matches: list[KeywordIntentMatch] = []

        for intent, keywords in INTENT_KEYWORDS.items():
            matched = [keyword for keyword in keywords if keyword.lower() in normalized]
            if not matched:
                continue

            confidence = min(0.95, 0.48 + len(matched) * 0.12)
            scored_matches.append(
                KeywordIntentMatch(
                    intent=intent,
                    confidence=confidence,
                    matched_keywords=matched,
                )
            )

        if not scored_matches:
            return None

        return max(scored_matches, key=lambda item: item.confidence)

    def _classify_by_llm(
        self,
        *,
        user_query: str,
        keyword_match: KeywordIntentMatch | None,
    ) -> IntentRecognitionResult | None:
        keyword_hint = self._format_keyword_hint(keyword_match)
        system_prompt = self.prompt_loader.load("intent_classification/system.txt")
        user_prompt = self.prompt_loader.render(
            "intent_classification/user.txt",
            user_query=user_query,
            keyword_hint=keyword_hint,
        )

        try:
            with TokenUsageTracker.scoped(workflow="intent", node_name="intent_classifier"):
                raw_content = self.llm_service.generate_text(
                    user_text=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.0,
                )
            parsed = self._parse_json_object(raw_content)
            intent = parsed.get("intent")
            confidence = float(parsed.get("confidence", 0.0))
            reason = str(parsed.get("reason", "")).strip()

            if intent not in VALID_INTENTS:
                return None

            return IntentRecognitionResult(
                intent=intent,
                confidence=max(0.0, min(confidence, 1.0)),
                source="llm",
                reason=reason,
                keyword_match=keyword_match,
            )
        except Exception:
            return None

    @staticmethod
    def _format_keyword_hint(keyword_match: KeywordIntentMatch | None) -> str:
        if keyword_match is None:
            return "无明确关键词命中"

        keywords = "、".join(keyword_match.matched_keywords)
        return (
            f"候选意图: {keyword_match.intent}; "
            f"规则置信度: {keyword_match.confidence:.2f}; "
            f"命中关键词: {keywords}"
        )

    @staticmethod
    def _parse_json_object(raw_content: str) -> dict:
        stripped = raw_content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()

        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise ValueError("No JSON object found in LLM response.")

        return json.loads(match.group(0))
