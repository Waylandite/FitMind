from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Any
from typing import Protocol
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.graph import StateGraph

from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


class NutritionTool(Protocol):
    name: str
    description: str

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run a nutrition helper tool and return a JSON-serializable result."""


@dataclass(frozen=True)
class NutritionToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class NutritionToolConnectionContext:
    provider_name: str
    provider_type: str
    connected: bool
    tool_count: int
    tools: list[dict[str, Any]]
    source: str
    last_error: str | None = None


class NutritionToolProvider(Protocol):
    def connect(self) -> NutritionToolConnectionContext:
        """Prepare the provider and return the connected tool context."""

    def list_specs(self) -> list[NutritionToolSpec]:
        """Return tool specs exposed to the ReAct agent."""

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name."""


@dataclass(frozen=True)
class LocalFoodNutrition:
    food_id: str
    name: str
    aliases: tuple[str, ...]
    calories_kcal: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


LOCAL_FOOD_DATABASE: tuple[LocalFoodNutrition, ...] = (
    LocalFoodNutrition("egg", "鸡蛋", ("鸡蛋", "水煮蛋", "煎蛋"), Decimal("143"), Decimal("12.6"), Decimal("0.7"), Decimal("9.5")),
    LocalFoodNutrition("milk", "牛奶", ("牛奶", "纯牛奶"), Decimal("60"), Decimal("3.2"), Decimal("4.8"), Decimal("3.3")),
    LocalFoodNutrition("rice_cooked", "熟米饭", ("米饭", "白米饭", "熟米饭", "饭"), Decimal("116"), Decimal("2.6"), Decimal("25.9"), Decimal("0.3")),
    LocalFoodNutrition("chicken_breast", "鸡胸肉", ("鸡胸肉", "鸡胸", "熟鸡胸肉"), Decimal("165"), Decimal("31"), Decimal("0"), Decimal("3.6")),
    LocalFoodNutrition("beef_lean", "瘦牛肉", ("牛肉", "瘦牛肉"), Decimal("250"), Decimal("26"), Decimal("0"), Decimal("15")),
    LocalFoodNutrition("banana", "香蕉", ("香蕉",), Decimal("89"), Decimal("1.1"), Decimal("22.8"), Decimal("0.3")),
    LocalFoodNutrition("protein_powder", "蛋白粉", ("蛋白粉", "乳清蛋白"), Decimal("400"), Decimal("80"), Decimal("8"), Decimal("6")),
    LocalFoodNutrition("yogurt", "酸奶", ("酸奶", "无糖酸奶"), Decimal("72"), Decimal("3.5"), Decimal("9"), Decimal("3")),
    LocalFoodNutrition("sweet_potato", "红薯", ("红薯", "地瓜"), Decimal("86"), Decimal("1.6"), Decimal("20.1"), Decimal("0.1")),
    LocalFoodNutrition("toast", "吐司", ("吐司", "面包", "全麦面包"), Decimal("265"), Decimal("9"), Decimal("49"), Decimal("3.2")),
    LocalFoodNutrition("oats", "燕麦", ("燕麦", "燕麦片"), Decimal("389"), Decimal("16.9"), Decimal("66.3"), Decimal("6.9")),
    LocalFoodNutrition("apple", "苹果", ("苹果",), Decimal("52"), Decimal("0.3"), Decimal("13.8"), Decimal("0.2")),
)


PORTION_WEIGHT_RULES: tuple[tuple[str, tuple[str, ...], Decimal, str], ...] = (
    ("鸡蛋", ("个", "只", "枚"), Decimal("50"), "一个鸡蛋按 50g 估算"),
    ("牛奶", ("杯", "盒"), Decimal("250"), "一杯/一盒牛奶按 250g 估算"),
    ("熟米饭", ("碗",), Decimal("150"), "一碗熟米饭按 150g 估算"),
    ("鸡胸肉", ("份",), Decimal("150"), "一份鸡胸肉按 150g 估算"),
    ("瘦牛肉", ("份",), Decimal("150"), "一份牛肉按 150g 估算"),
    ("香蕉", ("根", "个"), Decimal("120"), "一根香蕉按 120g 估算"),
    ("蛋白粉", ("勺",), Decimal("30"), "一勺蛋白粉按 30g 估算"),
    ("酸奶", ("杯", "盒"), Decimal("180"), "一杯/一盒酸奶按 180g 估算"),
    ("吐司", ("片",), Decimal("30"), "一片吐司按 30g 估算"),
)

CHINESE_NUMBER_MAP = {
    "半": Decimal("0.5"),
    "一": Decimal("1"),
    "两": Decimal("2"),
    "二": Decimal("2"),
    "三": Decimal("3"),
    "四": Decimal("4"),
    "五": Decimal("5"),
    "六": Decimal("6"),
    "七": Decimal("7"),
    "八": Decimal("8"),
    "九": Decimal("9"),
    "十": Decimal("10"),
}

TOOL_INPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "search_food_nutrition": {
        "type": "object",
        "properties": {
            "food_name": {"type": "string", "description": "用户提到的食物名称"},
        },
        "required": ["food_name"],
    },
    "estimate_food_weight": {
        "type": "object",
        "properties": {
            "food_text": {"type": "string", "description": "包含份量的用户原始食物片段"},
            "food_name": {"type": "string", "description": "标准食物名称"},
        },
        "required": ["food_text", "food_name"],
    },
    "calculate_nutrition": {
        "type": "object",
        "properties": {
            "food_name": {"type": "string"},
            "amount_g": {"type": "number"},
            "nutrition_per_100g": {"type": "object"},
            "confidence": {"type": "number"},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["food_name", "amount_g", "nutrition_per_100g"],
    },
    "sum_daily_nutrition": {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "object"}},
            "existing_daily_total": {"type": "object"},
        },
        "required": ["items"],
    },
}


def _decimal(value) -> Decimal:
    return Decimal(str(value))


def _round(value: Decimal, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _to_number(value: str | None) -> Decimal:
    if not value:
        return Decimal("1")
    if value in CHINESE_NUMBER_MAP:
        return CHINESE_NUMBER_MAP[value]
    return Decimal(value)


class SearchFoodNutritionTool:
    name = "search_food_nutrition"
    description = "查找本地标准食物营养数据，返回每 100g 热量、蛋白、碳水、脂肪。"

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        food_name = str(arguments.get("food_name") or "").strip()
        matches = []
        for food in LOCAL_FOOD_DATABASE:
            if food.name in food_name or food_name in food.name or any(alias in food_name or food_name in alias for alias in food.aliases):
                confidence = Decimal("0.96") if food.name == food_name or food_name in food.aliases else Decimal("0.82")
                matches.append((confidence, food))

        if not matches:
            return {
                "query": food_name,
                "best_match": None,
                "candidates": [],
                "confidence": 0,
                "source": "local_food_database",
                "warnings": ["本地食物库未找到匹配项"],
            }

        matches.sort(key=lambda item: item[0], reverse=True)
        confidence, food = matches[0]
        return {
            "query": food_name,
            "best_match": {
                "food_id": food.food_id,
                "name": food.name,
                "alias": list(food.aliases),
                "per_100g": {
                    "calories_kcal": float(food.calories_kcal),
                    "protein_g": float(food.protein_g),
                    "carbs_g": float(food.carbs_g),
                    "fat_g": float(food.fat_g),
                },
                "source": "local_food_database",
                "confidence": float(confidence),
            },
            "candidates": [
                {"food_id": candidate.food_id, "name": candidate.name, "confidence": float(score)}
                for score, candidate in matches[1:4]
            ],
            "confidence": float(confidence),
            "source": "local_food_database",
            "warnings": [],
        }


class EstimateFoodWeightTool:
    name = "estimate_food_weight"
    description = "把一碗、一杯、一份、两个等生活化份量估算成克数。"

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        food_text = str(arguments.get("food_text") or "").strip()
        food_name = str(arguments.get("food_name") or "").strip()

        gram_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|克)", food_text, flags=re.I)
        if gram_match:
            amount_g = _decimal(gram_match.group(1))
            return self._result(food_text, food_name, amount_g, "明确克数", Decimal("0.98"), [])

        ml_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ml|毫升)", food_text, flags=re.I)
        if ml_match:
            amount_g = _decimal(ml_match.group(1))
            return self._result(food_text, food_name, amount_g, "明确毫升数，按近似克数计算", Decimal("0.9"), [])

        for standard_food, units, grams_per_unit, warning in PORTION_WEIGHT_RULES:
            if standard_food not in food_name and standard_food not in food_text:
                continue
            unit_pattern = "|".join(re.escape(unit) for unit in units)
            portion_match = re.search(rf"(\d+(?:\.\d+)?|半|一|两|二|三|四|五|六|七|八|九|十)?\s*({unit_pattern})", food_text)
            if portion_match:
                count = _to_number(portion_match.group(1))
                return self._result(
                    food_text,
                    food_name,
                    count * grams_per_unit,
                    portion_match.group(2),
                    Decimal("0.76"),
                    [warning],
                )

        return self._result(
            food_text,
            food_name,
            Decimal("100"),
            "默认估算",
            Decimal("0.45"),
            ["未识别明确份量，按 100g 保守估算"],
        )

    @staticmethod
    def _result(food_text: str, food_name: str, amount_g: Decimal, label: str, confidence: Decimal, warnings: list[str]) -> dict[str, Any]:
        return {
            "food_text": food_text,
            "food_name": food_name,
            "estimated_amount": {
                "amount_g": float(_round(amount_g)),
                "unit": "g",
                "portion_label": label,
                "range_g": {
                    "min": float(_round(amount_g * Decimal("0.8"))),
                    "max": float(_round(amount_g * Decimal("1.2"))),
                },
            },
            "source": "portion_size_rules",
            "confidence": float(confidence),
            "warnings": warnings,
        }


class CalculateNutritionTool:
    name = "calculate_nutrition"
    description = "根据食物重量和每 100g 营养数据计算单项摄入。"

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        food_name = str(arguments.get("food_name") or "").strip()
        amount_g = _decimal(arguments.get("amount_g") or 0)
        nutrition_per_100g = arguments.get("nutrition_per_100g") or {}
        factor = amount_g / Decimal("100")
        nutrition = {
            "calories_kcal": _round(_decimal(nutrition_per_100g.get("calories_kcal") or 0) * factor),
            "protein_g": _round(_decimal(nutrition_per_100g.get("protein_g") or 0) * factor),
            "carbs_g": _round(_decimal(nutrition_per_100g.get("carbs_g") or 0) * factor),
            "fat_g": _round(_decimal(nutrition_per_100g.get("fat_g") or 0) * factor),
        }
        return {
            "food_name": food_name,
            "amount_g": float(_round(amount_g)),
            "nutrition": {key: float(value) for key, value in nutrition.items()},
            "formula": "per_100g * amount_g / 100",
            "source": "local_food_database",
            "confidence": float(arguments.get("confidence") or 0.8),
            "warnings": list(arguments.get("warnings") or []),
        }


class SumDailyNutritionTool:
    name = "sum_daily_nutrition"
    description = "汇总当天食物条目营养，输出今日累计热量和宏量营养。"

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        items = list(arguments.get("items") or [])
        existing = arguments.get("existing_daily_total") or {}
        totals = {
            "calories_kcal": _decimal(existing.get("calories_kcal") or 0),
            "protein_g": _decimal(existing.get("protein_g") or 0),
            "carbs_g": _decimal(existing.get("carbs_g") or 0),
            "fat_g": _decimal(existing.get("fat_g") or 0),
        }
        warnings: list[str] = []
        confidence_values: list[Decimal] = []

        for item in items:
            nutrition = item.get("nutrition") or {}
            totals["calories_kcal"] += _decimal(nutrition.get("calories_kcal") or 0)
            totals["protein_g"] += _decimal(nutrition.get("protein_g") or 0)
            totals["carbs_g"] += _decimal(nutrition.get("carbs_g") or 0)
            totals["fat_g"] += _decimal(nutrition.get("fat_g") or 0)
            warnings.extend(item.get("warnings") or [])
            confidence_values.append(_decimal(item.get("confidence") or 0.7))

        confidence = sum(confidence_values, Decimal("0")) / Decimal(len(confidence_values)) if confidence_values else Decimal("0")
        return {
            "daily_total": {
                "calories_kcal": float(_round(totals["calories_kcal"])),
                "protein_g": float(_round(totals["protein_g"])),
                "carbs_g": float(_round(totals["carbs_g"])),
                "fat_g": float(_round(totals["fat_g"])),
            },
            "item_count": len(items),
            "confidence": float(_round(confidence)),
            "warnings": warnings,
        }


class NutritionToolRegistry:
    def __init__(self, tools: list[NutritionTool] | None = None) -> None:
        default_tools: list[NutritionTool] = [
            SearchFoodNutritionTool(),
            EstimateFoodWeightTool(),
            CalculateNutritionTool(),
            SumDailyNutritionTool(),
        ]
        self._tools = {tool.name: tool for tool in tools or default_tools}

    def list_specs(self) -> list[NutritionToolSpec]:
        specs: list[NutritionToolSpec] = []
        for tool in self._tools.values():
            specs.append(
                NutritionToolSpec(
                    name=tool.name,
                    description=tool.description,
                    input_schema=TOOL_INPUT_SCHEMAS.get(tool.name, {"type": "object"}),
                )
            )
        return specs

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Nutrition tool is not registered: {name}")
        return tool.run(arguments)


class LocalMCPNutritionToolProvider:
    """
    MCP-ready local provider.

    The current implementation executes tools in-process so tests and local development remain stable.
    When an external MCP nutrition server is introduced, only this provider needs to be replaced by an
    adapter backed by langchain-mcp-adapters or an MCP client.
    """

    def __init__(self, registry: NutritionToolRegistry | None = None) -> None:
        self.registry = registry or NutritionToolRegistry()
        self.connection_context: NutritionToolConnectionContext | None = None

    def connect(self) -> NutritionToolConnectionContext:
        specs = self.list_specs()
        self.connection_context = NutritionToolConnectionContext(
            provider_name="fitmind-local-nutrition-tools",
            provider_type="local-mcp-ready",
            connected=True,
            tool_count=len(specs),
            tools=[spec.__dict__ for spec in specs],
            source="in_process_tool_registry",
        )
        return self.connection_context

    def list_specs(self) -> list[NutritionToolSpec]:
        return self.registry.list_specs()

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.connection_context is None:
            self.connect()
        return self.registry.run_tool(name, arguments)


class NutritionReActLoopState(TypedDict, total=False):
    user_query: str
    daily_context: dict[str, Any]
    current_date: str
    available_tools: list[dict[str, Any]]
    tool_connection_context: dict[str, Any]
    observations: list[dict[str, Any]]
    iteration: int
    max_iterations: int
    next_tool_call: dict[str, Any] | None
    final_payload: dict[str, Any] | None
    stop_reason: str | None
    llm_decisions: list[dict[str, Any]]


class NutritionLangGraphReActRunner:
    """
    LangGraph ReAct loop for nutrition extraction.

    The LLM decides either:
    - call exactly one nutrition tool, or
    - return the final structured payload.

    The graph owns loop control and stops at max_iterations even if the model keeps asking for tools.
    """

    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
        tool_provider: NutritionToolProvider | None = None,
        max_iterations: int = 8,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.tool_provider = tool_provider or LocalMCPNutritionToolProvider()
        self.tool_connection_context = self.tool_provider.connect()
        self.max_iterations = max_iterations
        self.graph = self._build_graph()

    def _connection_metadata(self) -> dict[str, Any]:
        context = self.tool_connection_context.__dict__.copy()
        context.pop("tools", None)
        return context

    def run(self, *, user_query: str, daily_context: dict[str, Any], current_date: str) -> dict[str, Any]:
        initial_state = self._build_initial_state(
            user_query=user_query,
            daily_context=daily_context,
            current_date=current_date,
        )
        final_state = self.graph.invoke(initial_state)
        return self._build_result(final_state)

    def stream_run(
        self,
        *,
        user_query: str,
        daily_context: dict[str, Any],
        current_date: str,
    ) -> Iterator[dict[str, Any]]:
        started_at = time.perf_counter()
        current_state = self._build_initial_state(
            user_query=user_query,
            daily_context=daily_context,
            current_date=current_date,
        )
        yield {
            "kind": "progress",
            "event": self._progress_event(
                status="queue",
                node="nutrition_react",
                title="饮食 ReAct 已进入执行队列",
                detail="准备连接营养工具并启动 LangGraph 状态机。",
                elapsed_ms=0,
            ),
        }

        for mode, chunk in self.graph.stream(
            current_state,
            stream_mode=["custom", "updates"],
        ):
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            if mode == "custom":
                event = chunk if isinstance(chunk, dict) else {"detail": str(chunk)}
                yield {
                    "kind": "progress",
                    "event": {
                        **event,
                        "workflow": event.get("workflow") or "nutrition_record",
                        "elapsed_ms": elapsed_ms,
                    },
                }
                continue

            if mode == "updates" and isinstance(chunk, dict):
                for node_name, updates in chunk.items():
                    if isinstance(updates, dict):
                        current_state.update(updates)
                    yield {
                        "kind": "progress",
                        "event": self._progress_event(
                            status="success",
                            node=str(node_name),
                            title=f"{self._node_label(str(node_name))}完成",
                            detail=self._summarize_node_update(str(node_name), updates),
                            iteration=current_state.get("iteration"),
                            elapsed_ms=elapsed_ms,
                        ),
                    }

        final_result = self._build_result(current_state)
        yield {
            "kind": "progress",
            "event": self._progress_event(
                status="success",
                node="nutrition_react",
                title="饮食 ReAct 执行完成",
                detail=(
                    f"完成 {final_result.get('iterations', 0)} 轮工具循环，"
                    f"停止原因：{final_result.get('stop_reason') or 'final'}。"
                ),
                iteration=final_result.get("iterations"),
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            ),
        }
        yield {"kind": "final", "result": final_result}

    def _build_initial_state(
        self,
        *,
        user_query: str,
        daily_context: dict[str, Any],
        current_date: str,
    ) -> NutritionReActLoopState:
        return {
            "user_query": user_query,
            "daily_context": daily_context,
            "current_date": current_date,
            "available_tools": self.tool_connection_context.tools,
            "tool_connection_context": self._connection_metadata(),
            "observations": [],
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "next_tool_call": None,
            "final_payload": None,
            "stop_reason": None,
            "llm_decisions": [],
        }

    def _build_result(self, final_state: NutritionReActLoopState) -> dict[str, Any]:
        if not final_state.get("final_payload"):
            final_state["final_payload"] = self._build_fallback_payload(final_state)
            final_state["stop_reason"] = final_state.get("stop_reason") or "max_iterations_or_no_final"

        return {
            "pattern": "LangGraph-ReAct",
            "iterations": final_state.get("iteration", 0),
            "max_iterations": final_state.get("max_iterations", self.max_iterations),
            "stop_reason": final_state.get("stop_reason") or "final",
            "final_payload": final_state.get("final_payload"),
            "observations": final_state.get("observations", []),
            "llm_decisions": final_state.get("llm_decisions", []),
            "tool_results": self._summarize_tool_results(final_state.get("observations", [])),
            "tool_connection_context": final_state.get("tool_connection_context") or self._connection_metadata(),
        }

    def _build_graph(self):
        graph = StateGraph(NutritionReActLoopState)
        graph.add_node("llm_decide", self._llm_decide)
        graph.add_node("tool_execute", self._tool_execute)
        graph.set_entry_point("llm_decide")
        graph.add_conditional_edges(
            "llm_decide",
            self._route_after_decide,
            {
                "tool_execute": "tool_execute",
                "end": END,
            },
        )
        graph.add_edge("tool_execute", "llm_decide")
        return graph.compile()

    def _llm_decide(self, state: NutritionReActLoopState) -> dict[str, Any]:
        self._write_progress(
            status="thinking",
            node="llm_decide",
            title="正在分析饮食输入",
            detail=(
                f"第 {state.get('iteration', 0) + 1} 轮：模型正在决定输出草稿，"
                "还是继续调用营养工具。"
            ),
            iteration=state.get("iteration", 0),
        )
        system_prompt = self.prompt_loader.load("nutrition_react_loop/system.txt")
        user_prompt = self.prompt_loader.render(
            "nutrition_react_loop/user.txt",
            current_date=state["current_date"],
            user_query=state["user_query"],
            daily_context=json.dumps(state["daily_context"], ensure_ascii=False, default=str),
            available_tools=json.dumps(state["available_tools"], ensure_ascii=False, default=str),
            tool_connection_context=json.dumps(
                state.get("tool_connection_context") or {},
                ensure_ascii=False,
                default=str,
            ),
            observations=json.dumps(state.get("observations", []), ensure_ascii=False, default=str),
            iteration=str(state.get("iteration", 0)),
            max_iterations=str(state.get("max_iterations", self.max_iterations)),
        )
        with TokenUsageTracker.scoped(workflow="nutrition_record", node_name="nutrition_react_decide"):
            raw_decision = self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
            )
        decision = self._parse_json_object(raw_decision)
        decisions = [*state.get("llm_decisions", []), decision]

        if decision.get("action") == "tool":
            self._write_progress(
                status="tool_call",
                node="llm_decide",
                title="模型选择调用工具",
                detail=decision.get("reason") or "模型认为需要工具补全营养估算。",
                iteration=state.get("iteration", 0),
                tool_name=decision.get("tool_name"),
                arguments=decision.get("arguments") or {},
            )
            return {
                "next_tool_call": {
                    "tool_name": decision.get("tool_name"),
                    "arguments": decision.get("arguments") or {},
                    "reason": decision.get("reason") or "",
                },
                "final_payload": None,
                "stop_reason": None,
                "llm_decisions": decisions,
            }

        if decision.get("action") == "final":
            self._write_progress(
                status="success",
                node="llm_decide",
                title="模型生成最终饮食草稿",
                detail="ReAct 已得到可用于确认入库的结构化饮食数据。",
                iteration=state.get("iteration", 0),
            )
            return {
                "next_tool_call": None,
                "final_payload": decision.get("payload") or {},
                "stop_reason": "final",
                "llm_decisions": decisions,
            }

        self._write_progress(
            status="error",
            node="llm_decide",
            title="模型决策格式异常",
            detail="本轮没有返回有效 action，系统会尝试用已有工具观察生成保守草稿。",
            iteration=state.get("iteration", 0),
        )
        return {
            "next_tool_call": None,
            "stop_reason": "invalid_llm_action",
            "llm_decisions": decisions,
        }

    def _tool_execute(self, state: NutritionReActLoopState) -> dict[str, Any]:
        tool_call = state.get("next_tool_call") or {}
        tool_name = str(tool_call.get("tool_name") or "")
        arguments = tool_call.get("arguments") or {}
        observation: dict[str, Any] = {
            "iteration": state.get("iteration", 0) + 1,
            "tool_name": tool_name,
            "arguments": arguments,
            "reason": tool_call.get("reason") or "",
        }
        self._write_progress(
            status="tool_call",
            node="tool_execute",
            title=f"正在执行工具：{tool_name or 'unknown'}",
            detail=observation["reason"] or "执行营养工具调用。",
            iteration=observation["iteration"],
            tool_name=tool_name,
            arguments=arguments,
        )
        try:
            observation["output"] = self.tool_provider.run_tool(tool_name, arguments)
            observation["ok"] = True
            self._write_progress(
                status="tool_output",
                node="tool_execute",
                title=f"工具返回：{tool_name or 'unknown'}",
                detail=self._preview_payload(observation["output"]),
                iteration=observation["iteration"],
                tool_name=tool_name,
                output=observation["output"],
            )
        except Exception as exc:  # noqa: BLE001 - tool errors must be returned to the agent loop.
            observation["output"] = {"error": str(exc)}
            observation["ok"] = False
            self._write_progress(
                status="error",
                node="tool_execute",
                title=f"工具失败：{tool_name or 'unknown'}",
                detail=str(exc),
                iteration=observation["iteration"],
                tool_name=tool_name,
            )

        return {
            "observations": [*state.get("observations", []), observation],
            "iteration": state.get("iteration", 0) + 1,
            "next_tool_call": None,
        }

    @staticmethod
    def _route_after_decide(state: NutritionReActLoopState) -> str:
        if state.get("final_payload") is not None or state.get("stop_reason"):
            return "end"
        if state.get("next_tool_call") and state.get("iteration", 0) < state.get("max_iterations", 0):
            return "tool_execute"
        return "end"

    @staticmethod
    def _parse_json_object(raw_content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", raw_content, flags=re.S)
        if not match:
            return {"action": "invalid", "raw_content": raw_content}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"action": "invalid", "raw_content": raw_content}
        return parsed if isinstance(parsed, dict) else {"action": "invalid", "raw_content": raw_content}

    @staticmethod
    def _summarize_tool_results(observations: list[dict[str, Any]]) -> dict[str, Any]:
        daily_total: dict[str, Any] | None = None
        calculated_items: list[dict[str, Any]] = []
        warnings: list[str] = []
        confidences: list[Decimal] = []

        for observation in observations:
            output = observation.get("output") or {}
            if not isinstance(output, dict):
                continue
            if observation.get("tool_name") == "calculate_nutrition":
                nutrition = output.get("nutrition") or {}
                calculated_items.append(
                    {
                        "food_name": output.get("food_name") or "",
                        "original_text": output.get("food_name") or "",
                        "amount_g": output.get("amount_g"),
                        "nutrition": nutrition,
                        "confidence": output.get("confidence") or 0,
                        "source": output.get("source") or "local_food_database",
                        "warnings": output.get("warnings") or [],
                    }
                )
                warnings.extend(output.get("warnings") or [])
                confidences.append(_decimal(output.get("confidence") or 0))
            if observation.get("tool_name") == "sum_daily_nutrition":
                daily_total = output.get("daily_total")
                warnings.extend(output.get("warnings") or [])
                confidences.append(_decimal(output.get("confidence") or 0))

        confidence = (
            float(_round(sum(confidences, Decimal("0")) / Decimal(len(confidences))))
            if confidences
            else 0
        )
        return {
            "daily_total": daily_total,
            "calculated_items": calculated_items,
            "warnings": list(dict.fromkeys(warnings)),
            "confidence": confidence,
            "tool_trace": observations,
        }

    @staticmethod
    def _build_fallback_payload(state: NutritionReActLoopState) -> dict[str, Any]:
        tool_results = NutritionLangGraphReActRunner._summarize_tool_results(
            state.get("observations", [])
        )
        daily_total = tool_results.get("daily_total") or {}
        calculated_items = tool_results.get("calculated_items") or []
        return {
            "record_date": state.get("current_date"),
            "nutrition": {
                "has_content": bool(calculated_items or state.get("user_query")),
                "raw_text": f"{state.get('current_date')} {state.get('user_query', '')}",
                "calories_estimate": daily_total.get("calories_kcal"),
                "protein_g_estimate": daily_total.get("protein_g"),
                "carbs_g_estimate": daily_total.get("carbs_g"),
                "fat_g_estimate": daily_total.get("fat_g"),
                "items": [
                    {
                        "food_name": item.get("food_name") or "",
                        "original_text": item.get("original_text") or "",
                        "amount_g": item.get("amount_g"),
                        "calories_kcal": (item.get("nutrition") or {}).get("calories_kcal"),
                        "protein_g": (item.get("nutrition") or {}).get("protein_g"),
                        "carbs_g": (item.get("nutrition") or {}).get("carbs_g"),
                        "fat_g": (item.get("nutrition") or {}).get("fat_g"),
                        "confidence": item.get("confidence") or 0,
                        "source": item.get("source") or "local_food_database",
                        "warnings": item.get("warnings") or [],
                    }
                    for item in calculated_items
                ],
            },
            "body_status": {"has_content": False, "raw_text": None},
            "confidence": tool_results.get("confidence") or 0,
            "missing_fields": tool_results.get("warnings") or ["ReAct 循环未得到模型 final，已用工具观察保守生成草稿"],
            "summary_text": "基于已完成的营养工具观察生成饮食记录草稿。",
        }

    @staticmethod
    def _node_label(node_name: str) -> str:
        labels = {
            "llm_decide": "模型决策节点",
            "tool_execute": "工具执行节点",
            "nutrition_react": "饮食 ReAct",
        }
        return labels.get(node_name, node_name)

    @classmethod
    def _progress_event(
        cls,
        *,
        status: str,
        node: str,
        title: str,
        detail: str,
        iteration: int | None = None,
        elapsed_ms: int | None = None,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "workflow": "nutrition_record",
            "status": status,
            "node": node,
            "title": title,
            "detail": detail,
        }
        if iteration is not None:
            event["iteration"] = iteration
        if elapsed_ms is not None:
            event["elapsed_ms"] = elapsed_ms
        if tool_name:
            event["tool_name"] = tool_name
        if arguments:
            event["arguments"] = cls._compact_payload(arguments)
        if output:
            event["output"] = cls._compact_payload(output)
        return event

    @classmethod
    def _write_progress(
        cls,
        *,
        status: str,
        node: str,
        title: str,
        detail: str,
        iteration: int | None = None,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
    ) -> None:
        try:
            writer = get_stream_writer()
        except RuntimeError:
            return

        writer(
            cls._progress_event(
                status=status,
                node=node,
                title=title,
                detail=detail,
                iteration=iteration,
                tool_name=tool_name,
                arguments=arguments,
                output=output,
            )
        )

    @staticmethod
    def _summarize_node_update(node_name: str, updates: Any) -> str:
        if not isinstance(updates, dict):
            return "节点状态已更新。"
        if node_name == "llm_decide":
            if updates.get("final_payload") is not None:
                return "模型已经输出最终结构化草稿。"
            tool_call = updates.get("next_tool_call") or {}
            if tool_call:
                return f"下一步将调用工具 {tool_call.get('tool_name') or 'unknown'}。"
            return updates.get("stop_reason") or "模型决策已记录。"
        if node_name == "tool_execute":
            observations = updates.get("observations") or []
            if observations:
                latest = observations[-1]
                status = "成功" if latest.get("ok") else "失败"
                return f"{latest.get('tool_name') or 'unknown'} 执行{status}。"
            return "工具执行状态已更新。"
        return "节点状态已更新。"

    @classmethod
    def _preview_payload(cls, payload: Any, max_length: int = 220) -> str:
        text = json.dumps(cls._compact_payload(payload), ensure_ascii=False, default=str)
        return text if len(text) <= max_length else f"{text[:max_length]}..."

    @classmethod
    def _compact_payload(cls, payload: Any) -> Any:
        if isinstance(payload, dict):
            compact: dict[str, Any] = {}
            for key, value in payload.items():
                if key in {"nutrition_per_100g", "items"} and isinstance(value, (dict, list)):
                    compact[key] = cls._compact_payload(value)
                elif isinstance(value, (dict, list)):
                    compact[key] = cls._compact_payload(value)
                else:
                    compact[key] = value
            return compact
        if isinstance(payload, list):
            return [cls._compact_payload(item) for item in payload[:8]]
        return payload
