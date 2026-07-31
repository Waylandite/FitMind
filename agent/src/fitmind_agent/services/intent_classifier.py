from __future__ import annotations

import json
import re

from fitmind_agent.schemas.intent import IntentCode
from fitmind_agent.schemas.intent import IntentCandidate
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
    "recent_health_summary": (
        "最近",
        "这几天",
        "总结",
        "回顾",
        "分析一下",
        "训练情况",
        "饮食情况",
        "身体状态",
        "恢复情况",
        "最近状态",
        "最近表现",
        "健康情况",
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
    "workout_history_query": (
        "训练历史",
        "查训练",
        "查询训练",
        "训练记录",
        "练了什么",
        "上周练",
        "上个月练",
        "卧推记录",
        "深蹲记录",
        "回顾训练",
    ),
    "weekly_trend_report": (
        "周报",
        "本周总结",
        "这周总结",
        "本周趋势",
        "这周趋势",
        "和上周比",
        "对比上周",
        "较上周",
        "最近是否进步",
        "最近有进步",
        "进步了吗",
        "趋势",
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
    "recent_health_summary",
    "today_workout_recommendation",
    "workout_history_query",
    "weekly_trend_report",
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

    def classify(self, user_query: str, context: str = "") -> IntentRecognitionResult:
        keyword_match = self.classify_by_keywords(user_query)
        contextual_query = f"最近对话（仅供补全指代，当前输入优先）：\n{context}\n\n当前输入：\n{user_query}" if context else user_query
        llm_result = self._classify_by_llm(user_query=contextual_query, keyword_match=keyword_match)

        if llm_result and llm_result.confidence >= self.confidence_threshold:
            return llm_result

        if keyword_match and keyword_match.confidence >= self.keyword_threshold:
            return IntentRecognitionResult(
                intent=keyword_match.intent,
                confidence=keyword_match.confidence,
                source="keyword",
                reason="关键词规则命中，模型置信度不足或模型识别失败。",
                keyword_match=keyword_match,
                candidates=[IntentCandidate(intent=keyword_match.intent, confidence=keyword_match.confidence)],
            )

        return IntentRecognitionResult(
            intent=llm_result.intent if llm_result else "unknown",
            confidence=llm_result.confidence if llm_result else 0.0,
            source="fallback",
            reason=llm_result.reason if llm_result else "未获得稳定意图。",
            keyword_match=keyword_match,
            candidates=llm_result.candidates if llm_result else [],
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

    def classify_clarification(self, original_query: str, last_question: str, answer: str) -> IntentRecognitionResult:
        """Dedicated, context-aware parser for an answer to a clarification."""
        keyword_match = self.classify_by_keywords(answer)
        system_prompt = self.prompt_loader.load("intent_clarification/system.txt")
        user_prompt = self.prompt_loader.render(
            "intent_clarification/user.txt",
            original_query=original_query,
            last_question=last_question,
            answer=answer,
        )
        result = self._classify_prompt(system_prompt, user_prompt, keyword_match, "intent_clarification")
        return result or IntentRecognitionResult(intent="unknown", confidence=0.0, source="fallback", reason="澄清解析失败。")

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

        return self._classify_prompt(system_prompt, user_prompt, keyword_match, "intent_classifier")

    def _classify_prompt(self, system_prompt: str, user_prompt: str, keyword_match: KeywordIntentMatch | None, node_name: str) -> IntentRecognitionResult | None:
        try:
            with TokenUsageTracker.scoped(workflow="intent", node_name=node_name):
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

            candidates = []
            for item in (parsed.get("candidates") or [])[:3]:
                if item.get("intent") in VALID_INTENTS:
                    candidates.append(IntentCandidate(
                        intent=item["intent"],
                        confidence=max(0.0, min(float(item.get("confidence", 0.0)), 1.0)),
                        reason=str(item.get("reason", "")).strip(),
                    ))
            if not candidates:
                candidates = [IntentCandidate(intent=intent, confidence=max(0.0, min(confidence, 1.0)), reason=reason)]
            candidates.sort(key=lambda item: item.confidence, reverse=True)
            return IntentRecognitionResult(
                intent=intent,
                confidence=max(0.0, min(confidence, 1.0)),
                source="llm",
                reason=reason,
                keyword_match=keyword_match,
                candidates=candidates,
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
