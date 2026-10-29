"""Keep the default test suite independent of model credentials and network calls."""

import os

import pytest


# Some orchestration tests instantiate the client before replacing individual calls.
# A dummy key allows construction without requiring a developer's real credentials.
os.environ["FITMIND_LLM_API_KEY"] = "test-only-no-network"


@pytest.fixture(autouse=True)
def block_real_model_client(monkeypatch):
    def blocked_client(*args, **kwargs):
        raise AssertionError("Tests must inject a model fake instead of calling the model API")

    monkeypatch.setattr("fitmind_agent.core.llm.OpenAI", blocked_client)
