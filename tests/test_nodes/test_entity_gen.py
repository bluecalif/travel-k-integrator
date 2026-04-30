from __future__ import annotations

import pytest
from unittest.mock import patch

from src.adapters.llm_adapter import MockLLM
from src.nodes.entity_gen import entity_gen
from src.state import BronzeState, CategorySaturation, EntityMeta


# --- 픽스처 ---

MINI_SKELETON = {
    "domain": "test-d",
    "categories": [
        {"slug": "transport",     "name": "교통"},
        {"slug": "accommodation", "name": "숙박"},
    ],
    "fields": [
        {"name": "price",    "type": "object", "categories": ["*"]},
        {"name": "tips",     "type": "string", "categories": ["*"]},
        {"name": "duration", "type": "string", "categories": ["transport"]},
        {"name": "location", "type": "object", "categories": ["accommodation"]},
    ],
}


def _make_state(
    transport_slugs: list[str] | None = None,
    accom_slugs: list[str] | None = None,
    transport_failures: int = 0,
    transport_saturated: bool = False,
) -> BronzeState:
    entity_registry: dict[str, EntityMeta] = {}
    for slug in (transport_slugs or []):
        entity_registry[f"test-d:transport:{slug}"] = EntityMeta(
            category="transport", name=slug, registered_at="2026-01-01T00:00:00+00:00", source="seed"
        )
    for slug in (accom_slugs or []):
        entity_registry[f"test-d:accommodation:{slug}"] = EntityMeta(
            category="accommodation", name=slug, registered_at="2026-01-01T00:00:00+00:00", source="seed"
        )
    return BronzeState(
        domain_skeleton=MINI_SKELETON,
        entity_registry=entity_registry,
        category_saturation={
            "transport": CategorySaturation(
                is_saturated=transport_saturated,
                consecutive_failures=transport_failures,
            ),
            "accommodation": CategorySaturation(),
        },
        current_cycle=1,
    )


# --- 정상 등록 ---

def test_registers_new_entity():
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(['{"slug": "shinkansen", "name": "신칸센"}'])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    assert "test-d:transport:shinkansen" in result["entity_registry"]


def test_new_entity_meta_source_and_cycle():
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(['{"slug": "shinkansen", "name": "신칸센"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    meta = result["entity_registry"]["test-d:transport:shinkansen"]
    assert meta.source == "entity_gen"
    assert meta.cycle == 1
    assert meta.category == "transport"


def test_creates_mandatory_gus_for_new_entity():
    """transport 적용 fields: price, tips, duration → GU 3개."""
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(['{"slug": "shinkansen", "name": "신칸센"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    new_gus = [g for g in result["gap_map"] if g.entity_key == "test-d:transport:shinkansen"]
    gu_fields = {g.field for g in new_gus}
    assert gu_fields == {"price", "tips", "duration"}
    assert all(g.status == "open" for g in new_gus)


def test_success_resets_consecutive_failures():
    state = _make_state(transport_slugs=["jr-pass"], transport_failures=1)
    mock_llm = MockLLM(['{"slug": "shinkansen", "name": "신칸센"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    assert result["category_saturation"]["transport"].consecutive_failures == 0


# --- de-dup 거부 ---

def test_dedup_same_slug_rejected():
    """후보 slug == 기존 slug (유사도 1.0 ≥ 0.85) → 등록 거부."""
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(['{"slug": "jr-pass", "name": "JR Pass 복제"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    assert "test-d:transport:jr-pass" not in [
        k for k in result["entity_registry"]
        if result["entity_registry"][k].source == "entity_gen"
    ]


def test_dedup_increments_consecutive_failures():
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(['{"slug": "jr-pass", "name": "복제"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    assert result["category_saturation"]["transport"].consecutive_failures == 1


# --- saturation ---

def test_two_failures_sets_saturated():
    """consecutive_failures가 이미 1이고, 이번에도 거부 → is_saturated = True."""
    state = _make_state(transport_slugs=["jr-pass"], transport_failures=1)
    mock_llm = MockLLM(['{"slug": "jr-pass", "name": "복제"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    sat = result["category_saturation"]["transport"]
    assert sat.is_saturated is True


def test_null_llm_response_increments_failures():
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(["null", "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    assert result["category_saturation"]["transport"].consecutive_failures == 1


def test_saturated_category_skipped():
    """is_saturated=True 카테고리는 LLM 호출 없이 건너뜀."""
    state = _make_state(transport_saturated=True)
    mock_llm = MockLLM(['{"slug": "shinkansen", "name": "신칸센"}'])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    # transport는 skipped → transport entity 추가 없음
    added_transport = [
        k for k, m in result["entity_registry"].items()
        if m.category == "transport" and m.source == "entity_gen"
    ]
    assert added_transport == []


def test_max_entities_per_category_saturates_without_failure_increment():
    """len(existing) >= max_entities_per_category → is_saturated, consecutive_failures 불변."""
    many_slugs = [f"entity-{i}" for i in range(20)]
    state = _make_state(transport_slugs=many_slugs)
    mock_llm = MockLLM(['{"slug": "new-entity", "name": "신규"}', "null"])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    sat = result["category_saturation"]["transport"]
    assert sat.is_saturated is True
    assert sat.consecutive_failures == 0  # failure count는 변하지 않음


def test_global_dedup_cross_category_slug_rejected():
    """다른 카테고리에 이미 존재하는 slug → 전역 de-dup으로 거부."""
    # transport:jr-pass 존재, accommodation에서 "jr-pass" 제안 → 거부
    state = _make_state(transport_slugs=["jr-pass"])
    mock_llm = MockLLM(["null", '{"slug": "jr-pass", "name": "JR Pass 숙박"}'])
    with patch("src.nodes.entity_gen.create_llm", return_value=mock_llm):
        result = entity_gen(state)
    added = [k for k, m in result["entity_registry"].items() if m.source == "entity_gen"]
    assert not any("jr-pass" in k for k in added)
    assert result["category_saturation"]["accommodation"].consecutive_failures == 1
