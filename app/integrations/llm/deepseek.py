import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from openai import APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

_OLLAMA_SEMAPHORE = asyncio.Semaphore(1)


class DeepSeekError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DeepSeekProvider:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client
        if client is None and self.settings.deepseek_api_key:
            self._client = AsyncOpenAI(
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
                timeout=30.0,
                max_retries=1,
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        if self.settings.llm_provider == "ollama":
            async with _OLLAMA_SEMAPHORE:
                return await self._chat(messages, model=model, temperature=temperature)
        return await self._chat(messages, model=model, temperature=temperature)

    async def _chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None,
        temperature: float,
    ) -> str:
        self._require_client()
        try:
            response = await self._client.chat.completions.create(
                model=model or self.settings.deepseek_chat_model,
                messages=messages,
                temperature=temperature,
                stream=False,
            )
            content = response.choices[0].message.content
            if not content:
                raise DeepSeekError("EMPTY_RESPONSE", "AI 服务返回了空内容")
            return content
        except DeepSeekError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        if self.settings.llm_provider == "ollama":
            async with _OLLAMA_SEMAPHORE:
                async for content in self._stream_chat(
                    messages, model=model, temperature=temperature
                ):
                    yield content
            return
        async for content in self._stream_chat(messages, model=model, temperature=temperature):
            yield content

    async def _stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None,
        temperature: float,
    ) -> AsyncIterator[str]:
        self._require_client()
        try:
            stream = await self._client.chat.completions.create(
                model=model or self.settings.deepseek_chat_model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as exc:
            raise self._map_error(exc) from exc

    async def structured[SchemaT: BaseModel](
        self,
        messages: list[dict[str, str]],
        output_schema: type[SchemaT],
        *,
        model: str | None = None,
    ) -> SchemaT:
        if self.settings.llm_provider == "ollama":
            async with _OLLAMA_SEMAPHORE:
                return await self._structured(messages, output_schema, model=model)
        return await self._structured(messages, output_schema, model=model)

    async def _structured[SchemaT: BaseModel](
        self,
        messages: list[dict[str, str]],
        output_schema: type[SchemaT],
        *,
        model: str | None,
    ) -> SchemaT:
        self._require_client()
        validation_error: Exception | None = None
        use_response_format = True
        schema_instruction = {
            "role": "system",
            "content": (
                "只返回一个合法 JSON 对象，不要 Markdown。必须满足此 JSON Schema："
                + json.dumps(output_schema.model_json_schema(), ensure_ascii=False)
            ),
        }
        for _attempt in range(2):
            try:
                request_options = {
                    "model": model or self.settings.deepseek_chat_model,
                    "messages": [schema_instruction, *messages],
                    "temperature": 0.1,
                    "stream": False,
                }
                if use_response_format:
                    request_options["response_format"] = {"type": "json_object"}
                response = await self._client.chat.completions.create(**request_options)
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("empty structured content")
                try:
                    return output_schema.model_validate_json(content)
                except (ValidationError, ValueError, json.JSONDecodeError):
                    start, end = content.find("{"), content.rfind("}")
                    if start < 0 or end <= start:
                        raise
                    return output_schema.model_validate_json(content[start : end + 1])
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                validation_error = exc
                continue
            except APIStatusError as exc:
                if use_response_format and exc.status_code == 400:
                    use_response_format = False
                    validation_error = exc
                    continue
                raise self._map_error(exc) from exc
            except Exception as exc:
                raise self._map_error(exc) from exc
        raise DeepSeekError("INVALID_STRUCTURE", "AI 结构化输出校验失败") from validation_error

    def _require_client(self) -> None:
        if self._client is None:
            raise DeepSeekError("NOT_CONFIGURED", "未配置大模型 API Key")

    @staticmethod
    def _map_error(exc: Exception) -> DeepSeekError:
        if isinstance(exc, APITimeoutError):
            return DeepSeekError("UPSTREAM_TIMEOUT", "AI 服务响应超时")
        if isinstance(exc, RateLimitError):
            return DeepSeekError("UPSTREAM_RATE_LIMIT", "AI 服务繁忙，请稍后重试")
        if isinstance(exc, APIStatusError) and exc.status_code in {402, 403}:
            return DeepSeekError("UPSTREAM_ACCOUNT", "AI 服务账户当前不可用")
        return DeepSeekError("UPSTREAM_ERROR", "AI 服务暂时不可用")
