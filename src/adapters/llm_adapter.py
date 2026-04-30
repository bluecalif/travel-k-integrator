from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LLMCallCounter:
    def __init__(self, llm: Any) -> None:
        self._llm = llm
        self.call_count: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0

    def invoke(self, prompt: str | list) -> Any:
        self.call_count += 1
        response = self._llm.invoke(prompt)
        usage = getattr(response, "usage_metadata", None)
        if usage:
            self.total_prompt_tokens += usage.get("input_tokens", 0)
            self.total_completion_tokens += usage.get("output_tokens", 0)
        return response

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    def __getattr__(self, name: str) -> Any:
        return getattr(self._llm, name)


def create_llm(config: Any = None, *, track_usage: bool = True) -> Any:
    if config is None:
        from src.config import BronzeConfig
        config = BronzeConfig.from_env()

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=config.llm_model,
        temperature=config.llm_temperature,
        max_tokens=config.llm_max_tokens,
        api_key=config.openai_api_key,
        max_retries=3,
    )
    if track_usage:
        return LLMCallCounter(llm)
    return llm


class MockLLM:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = list(responses or ['{"result": "mock"}'])
        self._call_index = 0
        self.calls: list[str] = []
        self.call_count: int = 0

    def invoke(self, prompt: str | list) -> Any:
        self.calls.append(str(prompt))
        self.call_count += 1
        text = self.responses[self._call_index % len(self.responses)]
        self._call_index += 1
        return _MockResponse(text)


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content
