from collections.abc import AsyncIterator
from typing import Any, Protocol

from pydantic import BaseModel


class LLMProvider(Protocol):
    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...

    def stream_chat(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]: ...

    async def structured[SchemaT: BaseModel](
        self,
        messages: list[dict[str, str]],
        output_schema: type[SchemaT],
        **kwargs: Any,
    ) -> SchemaT: ...
