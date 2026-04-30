from __future__ import annotations

from unittest.mock import patch

import pytest

from src.config import BronzeConfig
from src.nodes.plan import plan
from src.state import BronzeState, EntityMeta, GU


# --- 픽스처 ---

MINI_SKELETON = {
    "domain": "test-d",
    "categories": [
        {"slug": "transport", "name": "교통"},
        {"slug": "dining", "name": "식당"},
    ],
    "fields": [
        {"name": "price",     "type": "object", "categories": ["*"]},
        {"name": "tips",      "type": "string", "categories": ["*"]},
        {"name": "duration",  "type": "string", "categories": ["transport"]},
        {"name": "etiquette", "type": "string", "categories": ["dining"]},
    ],
}


def _make_gu(gu_id: str, entity_key: str, field: str, status: str = "open") -> GU:
    return GU(
        gu_id=gu_id,
        entity_key=entity_key,
        field=field,
        status=status,
        created_at="2026-01-01T00:00:00+00:00",
    )


def _make_state(
    entities: list[tuple[str, str, str]] | None = None,
    gus: list[GU] | None = None,
) -> BronzeState:
    entity_registry: dict[str, EntityMeta] = {}
    for ek, cat, name in (entities or []):
        entity_registry[ek] = EntityMeta(
            category=cat,
            name=name,
            registered_at="2026-01-01T00:00:00+00:00",
            source="seed",
        )
    return BronzeState(
        domain_skeleton=MINI_SKELETON,
        entity_registry=entity_registry,
        gap_map=gus or [],
    )


_DEFAULT_CONFIG = BronzeConfig(max_gus_per_cycle=25)


# --- 카테고리별 entity 선정 ---

def test_selects_entity_per_category():
    """카테고리마다 1개 entity가 target_entities에 선정된다."""
    state = _make_state(
        entities=[
            ("test-d:transport:jr-pass", "transport", "JR Pass"),
            ("test-d:dining:sushi-saito", "dining", "Sushi Saito"),
        ],
        gus=[
            _make_gu("GU-0001", "test-d:transport:jr-pass", "price"),
            _make_gu("GU-0002", "test-d:dining:sushi-saito", "price"),
        ],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    assert result["target_entities"]["transport"] == "test-d:transport:jr-pass"
    assert result["target_entities"]["dining"] == "test-d:dining:sushi-saito"


def test_selects_entity_with_most_open_gus():
    """open GU가 더 많은 entity가 선택된다."""
    state = _make_state(
        entities=[
            ("test-d:transport:jr-pass", "transport", "JR Pass"),
            ("test-d:transport:suica", "transport", "Suica"),
        ],
        gus=[
            _make_gu("GU-0001", "test-d:transport:jr-pass", "price"),
            _make_gu("GU-0002", "test-d:transport:jr-pass", "tips"),
            _make_gu("GU-0003", "test-d:transport:jr-pass", "duration"),
            _make_gu("GU-0004", "test-d:transport:suica", "price"),
        ],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    assert result["target_entities"]["transport"] == "test-d:transport:jr-pass"


def test_plan_queue_contains_selected_gu_ids():
    """plan_queue는 선정 entity의 open GU ID 목록을 포함한다."""
    state = _make_state(
        entities=[("test-d:transport:jr-pass", "transport", "JR Pass")],
        gus=[
            _make_gu("GU-0001", "test-d:transport:jr-pass", "price"),
            _make_gu("GU-0002", "test-d:transport:jr-pass", "tips"),
        ],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    assert "GU-0001" in result["plan_queue"]
    assert "GU-0002" in result["plan_queue"]


# --- 25 cap ---

def test_plan_queue_capped_at_max_gus():
    """open GU가 cap을 초과해도 plan_queue는 max_gus_per_cycle 이하."""
    gus = [
        _make_gu(f"GU-{i:04d}", "test-d:transport:jr-pass", f"f{i}")
        for i in range(1, 16)  # 15개
    ]
    state = _make_state(
        entities=[("test-d:transport:jr-pass", "transport", "JR Pass")],
        gus=gus,
    )
    cap_config = BronzeConfig(max_gus_per_cycle=5)
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=cap_config):
        result = plan(state)
    assert len(result["plan_queue"]) == 5


# --- skip 조건 ---

def test_category_with_no_entities_skipped():
    """entity가 없는 카테고리는 target_entities에 포함되지 않는다."""
    state = _make_state(
        entities=[("test-d:transport:jr-pass", "transport", "JR Pass")],
        gus=[_make_gu("GU-0001", "test-d:transport:jr-pass", "price")],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    assert "dining" not in result["target_entities"]


def test_category_with_no_open_gus_skipped():
    """entity가 있어도 open GU가 없으면 target_entities에서 제외된다."""
    state = _make_state(
        entities=[
            ("test-d:transport:jr-pass", "transport", "JR Pass"),
            ("test-d:dining:sushi-saito", "dining", "Sushi Saito"),
        ],
        gus=[
            _make_gu("GU-0001", "test-d:transport:jr-pass", "price"),
            _make_gu("GU-0002", "test-d:dining:sushi-saito", "price", status="resolved"),
        ],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    assert "transport" in result["target_entities"]
    assert "dining" not in result["target_entities"]


# --- gap_gen ---

def test_gap_gen_creates_missing_field_gus():
    """선정 entity에 GU가 없는 applicable field에 open GU를 신규 생성한다."""
    # jr-pass의 "price" GU만 있음 → gap_gen이 "tips", "duration" GU 생성해야 함
    state = _make_state(
        entities=[("test-d:transport:jr-pass", "transport", "JR Pass")],
        gus=[_make_gu("GU-0001", "test-d:transport:jr-pass", "price")],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    new_gu_fields = {g.field for g in result["gap_map"] if g.entity_key == "test-d:transport:jr-pass"}
    assert "tips" in new_gu_fields
    assert "duration" in new_gu_fields


def test_gap_gen_does_not_duplicate_existing_gus():
    """이미 GU(어떤 status라도)가 있는 field에는 GU를 추가 생성하지 않는다."""
    state = _make_state(
        entities=[("test-d:transport:jr-pass", "transport", "JR Pass")],
        gus=[
            _make_gu("GU-0001", "test-d:transport:jr-pass", "price"),
            _make_gu("GU-0002", "test-d:transport:jr-pass", "tips", status="resolved"),
            _make_gu("GU-0003", "test-d:transport:jr-pass", "duration", status="failed"),
        ],
    )
    with patch("src.nodes.plan.BronzeConfig.from_env", return_value=_DEFAULT_CONFIG):
        result = plan(state)
    # gap_map에 추가된 GU가 없어야 함 (이미 모든 field에 GU 존재)
    assert len(result["gap_map"]) == 3
