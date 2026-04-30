from __future__ import annotations

from unittest.mock import patch

from src.adapters.llm_adapter import MockLLM
from src.config import BronzeConfig
from src.nodes.collect import collect
from src.state import BronzeState, EntityMeta, GU


# --- 픽스처 ---

MINI_SKELETON = {
    "domain": "test-d",
    "categories": [{"slug": "transport", "name": "교통"}],
    "fields": [{"name": "price", "type": "object", "categories": ["*"]}],
}

_DEFAULT_CONFIG = BronzeConfig(gu_max_attempts=3)

_EK = "test-d:transport:jr-pass"


class MockSearch:
    def __init__(self, results_per_call: list[list[dict]] | None = None) -> None:
        self._results = results_per_call or []
        self._index = 0

    def search(self, query: str) -> list[dict]:
        if self._index >= len(self._results):
            return []
        r = self._results[self._index]
        self._index += 1
        return r


def _make_gu(gu_id: str, entity_key: str, field: str, status: str = "open", attempts: int = 0) -> GU:
    return GU(
        gu_id=gu_id,
        entity_key=entity_key,
        field=field,
        status=status,
        created_at="2026-01-01T00:00:00+00:00",
        attempts=attempts,
    )


def _make_state(plan_queue: list[str], gus: list[GU], with_entity: bool = True) -> BronzeState:
    entity_registry = {}
    if with_entity:
        entity_registry[_EK] = EntityMeta(
            category="transport",
            name="JR Pass",
            registered_at="2026-01-01T00:00:00+00:00",
            source="seed",
        )
    return BronzeState(
        domain_skeleton=MINI_SKELETON,
        entity_registry=entity_registry,
        gap_map=gus,
        plan_queue=plan_queue,
    )


def _run(state: BronzeState, mock_llm: MockLLM, mock_search: MockSearch) -> dict:
    with patch("src.nodes.collect.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG), \
         patch("src.nodes.collect.create_llm", return_value=mock_llm), \
         patch("src.nodes.collect.TavilySearchAdapter", return_value=mock_search):
        return collect(state)


# --- EU 생성 ---

def test_creates_eu_for_each_search_result():
    """search 결과 N개 → EU N개 생성."""
    gus = [_make_gu("GU-0001", _EK, "price")]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[
        {"url": "http://a.com", "title": "A", "snippet": "A price info"},
        {"url": "http://b.com", "title": "B", "snippet": "B price info"},
    ]])
    mock_llm = MockLLM(['{"value": "50000", "confidence": 0.8}'])
    result = _run(state, mock_llm, mock_search)
    assert len(result["evidence_units"]) == 2


def test_eu_created_even_when_claim_fails():
    """LLM이 null을 반환해도 EU는 생성된다 (evidence-first)."""
    gus = [_make_gu("GU-0001", _EK, "price")]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[{"url": "http://a.com", "title": "A", "snippet": "some text"}]])
    mock_llm = MockLLM(["null"])
    result = _run(state, mock_llm, mock_search)
    assert len(result["evidence_units"]) == 1
    assert len(result["pending_claims"]) == 0


# --- Claim 추출 ---

def test_claim_added_to_pending_claims():
    """LLM이 유효한 claim을 반환하면 pending_claims에 추가된다."""
    gus = [_make_gu("GU-0001", _EK, "price")]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[{"url": "http://a.com", "title": "A", "snippet": "JR Pass 50000 yen"}]])
    mock_llm = MockLLM(['{"value": "50000 JPY", "confidence": 0.9}'])
    result = _run(state, mock_llm, mock_search)
    assert len(result["pending_claims"]) == 1


def test_claim_contains_required_fields():
    """추출된 claim은 필수 필드를 모두 포함한다."""
    gus = [_make_gu("GU-0001", _EK, "price")]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[{"url": "http://a.com", "title": "A", "snippet": "50000 yen"}]])
    mock_llm = MockLLM(['{"value": "50000 JPY", "confidence": 0.8}'])
    result = _run(state, mock_llm, mock_search)
    claim = result["pending_claims"][0]
    assert claim["entity_key"] == _EK
    assert claim["field"] == "price"
    assert "value" in claim
    assert "confidence" in claim
    assert "eu_id" in claim
    assert claim["gu_id"] == "GU-0001"


# --- 0-claim → attempts ---

def test_zero_claim_increments_attempts():
    """claim 없으면 gu.attempts +1, status는 open 유지."""
    gus = [_make_gu("GU-0001", _EK, "price", attempts=0)]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[{"url": "http://a.com", "title": "A", "snippet": "text"}]])
    mock_llm = MockLLM(["null"])
    result = _run(state, mock_llm, mock_search)
    gu = next(g for g in result["gap_map"] if g.gu_id == "GU-0001")
    assert gu.attempts == 1
    assert gu.status == "open"


def test_empty_search_results_increments_attempts():
    """search 결과 없으면 attempts +1."""
    gus = [_make_gu("GU-0001", _EK, "price")]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[]])  # empty
    mock_llm = MockLLM([])
    result = _run(state, mock_llm, mock_search)
    gu = next(g for g in result["gap_map"] if g.gu_id == "GU-0001")
    assert gu.attempts == 1


def test_attempts_at_max_sets_gu_failed():
    """attempts가 gu_max_attempts에 도달하면 status="failed"."""
    gus = [_make_gu("GU-0001", _EK, "price", attempts=2)]
    state = _make_state(["GU-0001"], gus)
    mock_search = MockSearch([[{"url": "http://a.com", "title": "A", "snippet": "text"}]])
    mock_llm = MockLLM(["null"])
    result = _run(state, mock_llm, mock_search)
    gu = next(g for g in result["gap_map"] if g.gu_id == "GU-0001")
    assert gu.attempts == 3
    assert gu.status == "failed"


# --- skip 조건 ---

def test_non_open_gu_skipped():
    """resolved/failed GU는 plan_queue에 있어도 처리하지 않는다."""
    gus = [
        _make_gu("GU-0001", _EK, "price", status="resolved"),
        _make_gu("GU-0002", _EK, "price", status="failed"),
    ]
    state = _make_state(["GU-0001", "GU-0002"], gus)
    mock_search = MockSearch([])
    mock_llm = MockLLM([])
    result = _run(state, mock_llm, mock_search)
    assert len(result["evidence_units"]) == 0
    assert len(result["pending_claims"]) == 0
