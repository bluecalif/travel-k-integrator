from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# gpt-4.1-mini pricing (USD per token)
_LLM_INPUT_COST_PER_TOKEN = 0.15 / 1_000_000
_LLM_OUTPUT_COST_PER_TOKEN = 0.60 / 1_000_000
_SEARCH_COST_PER_CALL = 0.01


@dataclass
class CostGuard:
    budget_cap_usd: float

    llm_calls: int = 0
    search_calls: int = 0
    accumulated_usd: float = 0.0
    _killed: bool = field(default=False, repr=False)

    def record_llm_call(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        cost = (prompt_tokens * _LLM_INPUT_COST_PER_TOKEN
                + completion_tokens * _LLM_OUTPUT_COST_PER_TOKEN)
        self.llm_calls += 1
        self.accumulated_usd += cost
        self._check_budget()

    def record_search_call(self) -> None:
        self.search_calls += 1
        self.accumulated_usd += _SEARCH_COST_PER_CALL
        self._check_budget()

    def over_budget(self) -> bool:
        return self._killed

    def _check_budget(self) -> None:
        if not self._killed and self.accumulated_usd >= self.budget_cap_usd:
            logger.warning(
                "[cost_guard] budget cap %.2f USD 초과 (누적 %.4f USD) — kill",
                self.budget_cap_usd,
                self.accumulated_usd,
            )
            self._killed = True

    def to_dict(self) -> dict:
        return {
            "budget_cap_usd": self.budget_cap_usd,
            "accumulated_usd": round(self.accumulated_usd, 6),
            "llm_calls": self.llm_calls,
            "search_calls": self.search_calls,
            "over_budget": self._killed,
        }
