from fitmind_agent.services.nutrition_react_tools import LocalMCPNutritionToolProvider
from fitmind_agent.services.nutrition_react_tools import NutritionLangGraphReActRunner
from fitmind_agent.services.nutrition_react_tools import NutritionToolRegistry


def run_tool(name: str, arguments: dict) -> dict:
    return NutritionToolRegistry().run_tool(name, arguments)


def test_search_food_nutrition_finds_egg() -> None:
    result = run_tool("search_food_nutrition", {"food_name": "鸡蛋"})
    assert result["best_match"]["name"] == "鸡蛋"
    assert result["best_match"]["per_100g"]["protein_g"] > 10


def test_search_food_nutrition_returns_warning_for_unknown_food() -> None:
    result = run_tool("search_food_nutrition", {"food_name": "神秘套餐"})
    assert result["best_match"] is None
    assert result["warnings"]


def test_estimate_food_weight_uses_explicit_grams() -> None:
    result = run_tool("estimate_food_weight", {"food_text": "鸡胸肉200g", "food_name": "鸡胸肉"})
    assert result["estimated_amount"]["amount_g"] == 200
    assert result["confidence"] > 0.9


def test_estimate_food_weight_handles_egg_count() -> None:
    result = run_tool("estimate_food_weight", {"food_text": "两个鸡蛋", "food_name": "鸡蛋"})
    assert result["estimated_amount"]["amount_g"] == 100
    assert result["warnings"]


def test_estimate_food_weight_handles_rice_bowl() -> None:
    result = run_tool("estimate_food_weight", {"food_text": "一碗米饭", "food_name": "熟米饭"})
    assert result["estimated_amount"]["amount_g"] == 150


def test_estimate_food_weight_handles_milk_ml() -> None:
    result = run_tool("estimate_food_weight", {"food_text": "牛奶250ml", "food_name": "牛奶"})
    assert result["estimated_amount"]["amount_g"] == 250


def test_calculate_nutrition_scales_per_100g() -> None:
    result = run_tool(
        "calculate_nutrition",
        {
            "food_name": "鸡蛋",
            "amount_g": 100,
            "nutrition_per_100g": {
                "calories_kcal": 143,
                "protein_g": 12.6,
                "carbs_g": 0.7,
                "fat_g": 9.5,
            },
        },
    )
    assert result["nutrition"]["calories_kcal"] == 143
    assert result["nutrition"]["protein_g"] == 12.6


def test_calculate_nutrition_handles_half_portion() -> None:
    result = run_tool(
        "calculate_nutrition",
        {
            "food_name": "牛奶",
            "amount_g": 50,
            "nutrition_per_100g": {
                "calories_kcal": 60,
                "protein_g": 3.2,
                "carbs_g": 4.8,
                "fat_g": 3.3,
            },
        },
    )
    assert result["nutrition"]["calories_kcal"] == 30
    assert result["nutrition"]["protein_g"] == 1.6


def test_sum_daily_nutrition_adds_existing_total() -> None:
    result = run_tool(
        "sum_daily_nutrition",
        {
            "items": [
                {
                    "nutrition": {
                        "calories_kcal": 143,
                        "protein_g": 12.6,
                        "carbs_g": 0.7,
                        "fat_g": 9.5,
                    },
                    "confidence": 0.9,
                }
            ],
            "existing_daily_total": {
                "calories_kcal": 1000,
                "protein_g": 60,
                "carbs_g": 120,
                "fat_g": 30,
            },
        },
    )
    assert result["daily_total"]["calories_kcal"] == 1143
    assert result["daily_total"]["protein_g"] == 72.6


def test_sum_daily_nutrition_collects_warnings() -> None:
    result = run_tool(
        "sum_daily_nutrition",
        {
            "items": [
                {
                    "nutrition": {"calories_kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0},
                    "confidence": 0.3,
                    "warnings": ["份量不确定"],
                }
            ],
        },
    )
    assert "份量不确定" in result["warnings"]


def test_local_tool_provider_connects_and_returns_context() -> None:
    provider = LocalMCPNutritionToolProvider()
    context = provider.connect()
    assert context.connected is True
    assert context.provider_type == "local-mcp-ready"
    assert context.tool_count == 4
    assert {tool["name"] for tool in context.tools} == {
        "search_food_nutrition",
        "estimate_food_weight",
        "calculate_nutrition",
        "sum_daily_nutrition",
    }

    result = provider.run_tool("search_food_nutrition", {"food_name": "鸡蛋"})
    assert result["best_match"]["name"] == "鸡蛋"


class ScriptedLLMService:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate_text(self, **kwargs) -> str:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def test_langgraph_react_runner_executes_llm_selected_tools() -> None:
    llm = ScriptedLLMService(
        [
            '{"action":"tool","tool_name":"search_food_nutrition","arguments":{"food_name":"鸡蛋"},"reason":"先查标准营养"}',
            '{"action":"tool","tool_name":"estimate_food_weight","arguments":{"food_text":"两个鸡蛋","food_name":"鸡蛋"},"reason":"估算重量"}',
            '{"action":"tool","tool_name":"calculate_nutrition","arguments":{"food_name":"鸡蛋","amount_g":100,"nutrition_per_100g":{"calories_kcal":143,"protein_g":12.6,"carbs_g":0.7,"fat_g":9.5},"confidence":0.9,"warnings":[]},"reason":"计算单项营养"}',
            '{"action":"tool","tool_name":"sum_daily_nutrition","arguments":{"items":[{"nutrition":{"calories_kcal":143,"protein_g":12.6,"carbs_g":0.7,"fat_g":9.5},"confidence":0.9,"warnings":[]}],"existing_daily_total":{}},"reason":"汇总当天摄入"}',
            '{"action":"final","payload":{"record_date":"2026-06-14","nutrition":{"has_content":true,"raw_text":"2026-06-14 早餐两个鸡蛋","calories_estimate":143,"protein_g_estimate":12.6,"carbs_g_estimate":0.7,"fat_g_estimate":9.5,"items":[{"food_name":"鸡蛋","original_text":"两个鸡蛋","amount_g":100,"calories_kcal":143,"protein_g":12.6,"carbs_g":0.7,"fat_g":9.5,"confidence":0.9,"source":"local_food_database","warnings":[]}]},"body_status":{"has_content":false,"raw_text":null},"confidence":0.9,"missing_fields":[],"summary_text":"记录两个鸡蛋。"},"reason":"工具结果足够"}',
        ]
    )
    runner = NutritionLangGraphReActRunner(llm_service=llm, max_iterations=6)
    result = runner.run(
        user_query="早餐两个鸡蛋",
        current_date="2026-06-14",
        daily_context={"record_date": "2026-06-14", "nutrition": None},
    )
    assert result["stop_reason"] == "final"
    assert result["iterations"] == 4
    assert [step["tool_name"] for step in result["observations"]] == [
        "search_food_nutrition",
        "estimate_food_weight",
        "calculate_nutrition",
        "sum_daily_nutrition",
    ]
    assert result["final_payload"]["nutrition"]["items"][0]["food_name"] == "鸡蛋"
    assert result["tool_connection_context"]["connected"] is True
    assert result["tool_connection_context"]["tool_count"] == 4
    assert "tools" not in result["tool_connection_context"]


def test_langgraph_react_runner_stops_at_max_iterations() -> None:
    llm = ScriptedLLMService(
        [
            '{"action":"tool","tool_name":"search_food_nutrition","arguments":{"food_name":"鸡蛋"},"reason":"重复请求"}',
        ]
    )
    runner = NutritionLangGraphReActRunner(llm_service=llm, max_iterations=2)
    result = runner.run(
        user_query="早餐两个鸡蛋",
        current_date="2026-06-14",
        daily_context={"record_date": "2026-06-14", "nutrition": None},
    )
    assert result["iterations"] == 2
    assert result["stop_reason"] == "max_iterations_or_no_final"
    assert result["final_payload"]["nutrition"]["has_content"] is True
