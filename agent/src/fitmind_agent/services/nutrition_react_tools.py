from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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


class NutritionToolRegistry:
    """Tool registry reserved for the nutrition ReAct workflow.

    The first version keeps the registry pluggable without binding to a specific MCP provider.
    Future MCP tools can be adapted to the NutritionTool protocol and registered here.
    """

    def __init__(self, tools: list[NutritionTool] | None = None) -> None:
        self._tools = {tool.name: tool for tool in tools or []}

    def list_specs(self) -> list[NutritionToolSpec]:
        specs: list[NutritionToolSpec] = []
        for tool in self._tools.values():
            specs.append(
                NutritionToolSpec(
                    name=tool.name,
                    description=tool.description,
                    input_schema={"type": "object"},
                )
            )
        return specs

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Nutrition tool is not registered: {name}")
        return tool.run(arguments)


class NutritionReActToolContextBuilder:
    def __init__(self, registry: NutritionToolRegistry | None = None) -> None:
        self.registry = registry or NutritionToolRegistry()

    def build_context(self, *, user_query: str, daily_context: dict) -> dict:
        return {
            "pattern": "ReAct-ready",
            "tool_policy": (
                "当接入 MCP 营养工具后，先把用户饮食拆成食物和份量，再调用工具查询或计算，"
                "最后汇总为今日累计营养字段。当前未注册工具时，模型只能做保守估算。"
            ),
            "available_tools": [spec.__dict__ for spec in self.registry.list_specs()],
            "tool_results": [],
            "input_snapshot": {
                "user_query": user_query,
                "daily_context": daily_context,
            },
        }
