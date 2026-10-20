from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.llm.deepseek import DeepSeekError, DeepSeekProvider


class StructuredAnswer(BaseModel):
    value: str


class FakeCompletions:
    def __init__(self, contents: list[str | None]) -> None:
        self.contents = contents
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.contents.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def fake_provider(contents: list[str | None]) -> tuple[DeepSeekProvider, FakeCompletions]:
    completions = FakeCompletions(contents)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    settings = Settings(_env_file=None, deepseek_api_key="environment-only-test-key")
    return DeepSeekProvider(settings=settings, client=client), completions


@pytest.mark.asyncio
async def test_structured_retries_once_after_invalid_json() -> None:
    provider, completions = fake_provider(["not-json", '{"value":"ok"}'])
    result = await provider.structured([{"role": "user", "content": "test"}], StructuredAnswer)
    assert result.value == "ok"
    assert len(completions.calls) == 2
    assert completions.calls[0]["model"] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_structured_rejects_two_invalid_responses() -> None:
    provider, _ = fake_provider(["bad", "still bad"])
    with pytest.raises(DeepSeekError) as error:
        await provider.structured([{"role": "user", "content": "test"}], StructuredAnswer)
    assert error.value.code == "INVALID_STRUCTURE"


@pytest.mark.asyncio
async def test_missing_key_is_stable_business_error() -> None:
    provider = DeepSeekProvider(Settings(_env_file=None, deepseek_api_key=""))
    with pytest.raises(DeepSeekError) as error:
        await provider.chat([{"role": "user", "content": "test"}])
    assert error.value.code == "NOT_CONFIGURED"
