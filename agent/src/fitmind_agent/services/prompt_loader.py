from __future__ import annotations

from pathlib import Path


class PromptLoader:
    def __init__(self) -> None:
        self.prompts_root = Path(__file__).resolve().parent.parent / "prompts"

    def load(self, relative_path: str) -> str:
        return (self.prompts_root / relative_path).read_text(encoding="utf-8").strip()

    def render(self, relative_path: str, **variables: str) -> str:
        template = self.load(relative_path)
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", value)
        return template
