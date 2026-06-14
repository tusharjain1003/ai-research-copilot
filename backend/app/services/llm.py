import json
import logging
from typing import Optional

from openai import OpenAI, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class LLMConfigurationError(LLMError):
    pass


class LLMInvalidResponseError(LLMError):
    pass


class LLMService:

    def __init__(self) -> None:
        self._validate_config()
        self._client: Optional[OpenAI] = None

    def _validate_config(self) -> None:
        if not settings.llm_api_key:
            raise LLMConfigurationError(
                "LLM API key is not configured. "
                "Set RESEARCH_COPILOT_LLM_API_KEY environment variable."
            )

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
        return self._client

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[dict] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = self.client.chat.completions.create(**kwargs)
        except APIError as e:
            logger.exception("LLM API call failed")
            raise LLMError(f"LLM API call failed: {e}") from e

        content = response.choices[0].message.content
        if content is None:
            raise LLMInvalidResponseError("LLM returned empty response")

        return content.strip()

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict:
        content = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMInvalidResponseError(
                f"LLM returned invalid JSON: {e}\nRaw content: {content[:500]}"
            ) from e
