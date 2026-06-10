from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMMessage


def test_llm_chat_request_schema() -> None:
    payload = LLMChatRequest(
        messages=[
            LLMMessage(role="user", content="你好，请用一句话介绍你自己。"),
        ]
    )

    assert payload.messages[0].role == "user"
