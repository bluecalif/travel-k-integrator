from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 1.0
BACKOFF_FACTOR = 2.0


def _retry_with_backoff(func: Any, *args: Any, max_retries: int = MAX_RETRIES, **kwargs: Any) -> Any:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if not re.search(r"429|5\d\d|rate", str(exc).lower()) or attempt == max_retries:
                raise
            wait = BACKOFF_BASE * (BACKOFF_FACTOR ** attempt)
            logger.warning("Retry %d/%d after %.1fs — %s", attempt + 1, max_retries, wait, exc)
            time.sleep(wait)
    raise last_exc  # type: ignore[misc]


class TavilySearchAdapter:
    def __init__(self, config: Any = None) -> None:
        if config is None:
            from src.config import BronzeConfig
            config = BronzeConfig.from_env()

        from tavily import TavilyClient

        self._client = TavilyClient(api_key=config.tavily_api_key)
        self.search_calls: int = 0

    def search(self, query: str) -> list[dict]:
        self.search_calls += 1
        response = _retry_with_backoff(
            self._client.search,
            query=query,
            max_results=3,
        )
        results = []
        for item in response.get("results", []):
            results.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
            })
        logger.debug("search #%d: %r → %d results", self.search_calls, query, len(results))
        return results
