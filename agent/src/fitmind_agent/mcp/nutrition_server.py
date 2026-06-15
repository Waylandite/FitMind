from __future__ import annotations

from typing import Any

from fitmind_agent.services.nutrition_react_tools import NutritionToolRegistry


registry = NutritionToolRegistry()

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only when MCP deps are missing.
    FastMCP = None  # type: ignore[assignment]
    MCP_IMPORT_ERROR = exc
else:
    MCP_IMPORT_ERROR = None


if FastMCP is not None:
    mcp = FastMCP("fitmind-nutrition")

    @mcp.tool()
    def search_food_nutrition(food_name: str) -> dict[str, Any]:
        """查标准食物营养，返回每 100g 热量、蛋白、碳水和脂肪。"""
        return registry.run_tool("search_food_nutrition", {"food_name": food_name})

    @mcp.tool()
    def estimate_food_weight(food_text: str, food_name: str) -> dict[str, Any]:
        """把“一碗米饭/一杯牛奶/一份牛肉”等描述估算成克数。"""
        return registry.run_tool(
            "estimate_food_weight",
            {"food_text": food_text, "food_name": food_name},
        )

    @mcp.tool()
    def calculate_nutrition(
        food_name: str,
        amount_g: float,
        nutrition_per_100g: dict[str, Any],
        confidence: float = 0.8,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        """根据食物重量和每 100g 营养数据计算单项营养。"""
        return registry.run_tool(
            "calculate_nutrition",
            {
                "food_name": food_name,
                "amount_g": amount_g,
                "nutrition_per_100g": nutrition_per_100g,
                "confidence": confidence,
                "warnings": warnings or [],
            },
        )

    @mcp.tool()
    def sum_daily_nutrition(
        items: list[dict[str, Any]],
        existing_daily_total: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """汇总当天食物条目营养，输出今日累计热量和宏量营养。"""
        return registry.run_tool(
            "sum_daily_nutrition",
            {
                "items": items,
                "existing_daily_total": existing_daily_total or {},
            },
        )


def main() -> None:
    if FastMCP is None:
        raise RuntimeError(
            "MCP dependencies are not installed. Install the agent dependencies with "
            "`pip install -e .` after adding the `mcp` package."
        ) from MCP_IMPORT_ERROR
    mcp.run()


if __name__ == "__main__":
    main()
