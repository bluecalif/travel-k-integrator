from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.nodes.seed import _resolve_applicable_fields, seed
from src.state import BronzeState


# --- 픽스처 ---

MINI_SKELETON = {
    "domain": "test-d",
    "categories": [
        {"slug": "transport", "name": "교통"},
        {"slug": "payment",   "name": "결제"},
    ],
    "fields": [
        {"name": "price",      "type": "object", "categories": ["*"]},
        {"name": "tips",       "type": "string", "categories": ["*"]},
        {"name": "duration",   "type": "string", "categories": ["transport"]},
        {"name": "acceptance", "type": "string", "categories": ["payment"]},
    ],
}

MINI_SEED_PACK = {
    "domain": "test-d",
    "entities": [
        {
            "category": "transport",
            "slug": "jr-pass",
            "name": "JR Pass",
            "initial_knowledge": [
                {
                    "field": "price",
                    "value": {"7day_jpy": 50000},
                    "source_url": "https://example.com",
                    "source_title": "Test",
                    "snippet": "JR Pass 7-day costs 50000 yen.",
                }
            ],
        },
        {
            "category": "payment",
            "slug": "cash",
            "name": "현금",
            "initial_knowledge": [],
        },
    ],
}


@pytest.fixture
def bench_root(tmp_path: Path) -> Path:
    (tmp_path / "seed-pack.json").write_text(
        json.dumps(MINI_SEED_PACK), encoding="utf-8"
    )
    (tmp_path / "domain-skeleton.json").write_text(
        json.dumps(MINI_SKELETON), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def initial_state() -> BronzeState:
    return BronzeState(domain_skeleton=MINI_SKELETON)


@pytest.fixture
def lg_config(bench_root: Path) -> dict:
    return {"configurable": {"bench_root": str(bench_root)}}


# --- _resolve_applicable_fields 단위 테스트 ---

def test_resolve_applicable_fields_wildcard():
    fields = _resolve_applicable_fields("transport", MINI_SKELETON)
    assert "price" in fields
    assert "tips" in fields


def test_resolve_applicable_fields_specific():
    fields = _resolve_applicable_fields("transport", MINI_SKELETON)
    assert "duration" in fields
    assert "acceptance" not in fields


def test_resolve_applicable_fields_payment():
    fields = _resolve_applicable_fields("payment", MINI_SKELETON)
    assert "acceptance" in fields
    assert "duration" not in fields


# --- seed 노드 기본 동작 ---

def test_seed_registers_all_entities(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    reg = result["entity_registry"]
    assert "test-d:transport:jr-pass" in reg
    assert "test-d:payment:cash" in reg


def test_seed_entity_meta_fields(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    meta = result["entity_registry"]["test-d:transport:jr-pass"]
    assert meta.category == "transport"
    assert meta.source == "seed"
    assert meta.cycle is None


# --- KU / EU (불변원칙 2, 3) ---

def test_seed_creates_one_active_ku_per_initial_knowledge(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    kus = result["knowledge_units"]
    # jr-pass 1개 initial_knowledge → KU 1개
    assert len(kus) == 1
    assert kus[0].status == "active"
    assert kus[0].field == "price"
    assert kus[0].entity_key == "test-d:transport:jr-pass"


def test_seed_active_ku_has_evidence_link(initial_state, lg_config):
    """불변원칙 3: active KU는 EU≥1 없이 active 불가."""
    result = seed(initial_state, lg_config)
    for ku in result["knowledge_units"]:
        if ku.status == "active":
            assert len(ku.evidence_links) >= 1


def test_seed_eu_count_equals_initial_knowledge_count(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    assert len(result["evidence_units"]) == len(result["knowledge_units"])


def test_seed_ku_evidence_links_point_to_existing_eu(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    eu_ids = {eu.eu_id for eu in result["evidence_units"]}
    for ku in result["knowledge_units"]:
        for eu_id in ku.evidence_links:
            assert eu_id in eu_ids


# --- mandatory GU ---

def test_seed_mandatory_gus_for_jr_pass(initial_state, lg_config):
    """transport 적용 fields: price, tips, duration (3개). price는 covered → GU 2개."""
    result = seed(initial_state, lg_config)
    jr_gus = [
        gu for gu in result["gap_map"]
        if gu.entity_key == "test-d:transport:jr-pass"
    ]
    gu_fields = {gu.field for gu in jr_gus}
    assert gu_fields == {"tips", "duration"}


def test_seed_mandatory_gus_for_cash(initial_state, lg_config):
    """payment 적용 fields: price, tips, acceptance (3개). initial_knowledge 없음 → GU 3개."""
    result = seed(initial_state, lg_config)
    cash_gus = [
        gu for gu in result["gap_map"]
        if gu.entity_key == "test-d:payment:cash"
    ]
    gu_fields = {gu.field for gu in cash_gus}
    assert gu_fields == {"price", "tips", "acceptance"}


def test_seed_all_gus_open(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    for gu in result["gap_map"]:
        assert gu.status == "open"


def test_seed_no_gu_for_covered_field(initial_state, lg_config):
    """initial_knowledge로 커버된 field(price)는 GU 생성 안 됨."""
    result = seed(initial_state, lg_config)
    jr_gus = [
        gu for gu in result["gap_map"]
        if gu.entity_key == "test-d:transport:jr-pass"
    ]
    assert all(gu.field != "price" for gu in jr_gus)


# --- category_saturation ---

def test_seed_category_saturation_initialized(initial_state, lg_config):
    result = seed(initial_state, lg_config)
    sat = result["category_saturation"]
    assert "transport" in sat
    assert "payment" in sat
    assert sat["transport"].is_saturated is False
    assert sat["transport"].consecutive_failures == 0


# --- 재진입 방지 (idempotent) ---

def test_seed_noop_if_already_initialized(initial_state, lg_config):
    """entity_registry가 이미 있으면 no-op 반환."""
    result1 = seed(initial_state, lg_config)
    from dataclasses import replace
    state2 = BronzeState(
        domain_skeleton=MINI_SKELETON,
        entity_registry=result1["entity_registry"],
    )
    result2 = seed(state2, lg_config)
    assert result2 == {}
