from __future__ import annotations

import pytest

from src.nodes.integrate import _same_value, integrate
from src.state import BronzeState, GU, KU


# --- 픽스처 ---

MINI_SKELETON = {
    "domain": "test-d",
    "categories": [{"slug": "transport", "name": "교통"}],
    "fields": [{"name": "price", "type": "object", "categories": ["*"]}],
}

_EK = "test-d:transport:jr-pass"


def _make_ku(
    ku_id: str,
    entity_key: str,
    field: str,
    value: object,
    confidence: float = 0.8,
    status: str = "active",
    evidence_links: list[str] | None = None,
) -> KU:
    return KU(
        ku_id=ku_id,
        entity_key=entity_key,
        field=field,
        value=value,
        confidence=confidence,
        status=status,
        evidence_links=evidence_links if evidence_links is not None else ["EU-0001"],
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _make_gu(gu_id: str, entity_key: str, field: str, status: str = "open") -> GU:
    return GU(
        gu_id=gu_id,
        entity_key=entity_key,
        field=field,
        status=status,
        created_at="2026-01-01T00:00:00+00:00",
    )


def _make_claim(
    gu_id: str,
    entity_key: str,
    field: str,
    value: object,
    confidence: float = 0.8,
    eu_id: str = "EU-0002",
) -> dict:
    return {
        "gu_id": gu_id,
        "entity_key": entity_key,
        "field": field,
        "value": value,
        "confidence": confidence,
        "eu_id": eu_id,
    }


def _make_state(
    knowledge_units: list[KU] | None = None,
    gap_map: list[GU] | None = None,
    pending_claims: list[dict] | None = None,
) -> BronzeState:
    return BronzeState(
        domain_skeleton=MINI_SKELETON,
        knowledge_units=knowledge_units or [],
        gap_map=gap_map or [],
        pending_claims=pending_claims or [],
    )


# --- _same_value ---

def test_same_value_exact_int():
    assert _same_value(50000, 50000) is True


def test_same_value_exact_string():
    assert _same_value("50000 JPY", "50000 JPY") is True


def test_same_value_number_comma_normalization():
    """'50,000' ↔ 50000 — 숫자 정규화."""
    assert _same_value("50,000", 50000) is True


def test_same_value_different_numbers():
    assert _same_value(50000, 29650) is False


def test_same_value_dict_exact():
    assert _same_value({"7day": 50000}, {"7day": 50000}) is True


def test_same_value_dict_different():
    assert _same_value({"7day": 50000}, {"7day": 29650}) is False


# --- Case A: 신규 KU ---

def test_case_a_creates_active_ku():
    """active KU 없을 때 → 신규 KU(status=active) 생성."""
    claim = _make_claim("GU-0001", _EK, "price", 50000)
    state = _make_state(
        gap_map=[_make_gu("GU-0001", _EK, "price")],
        pending_claims=[claim],
    )
    result = integrate(state)
    active = [k for k in result["knowledge_units"] if k.status == "active" and k.field == "price"]
    assert len(active) == 1
    assert active[0].value == 50000


def test_case_a_resolves_gu():
    """Case A → GU status=resolved, resolved_at 설정."""
    claim = _make_claim("GU-0001", _EK, "price", 50000)
    state = _make_state(
        gap_map=[_make_gu("GU-0001", _EK, "price")],
        pending_claims=[claim],
    )
    result = integrate(state)
    gu = next(g for g in result["gap_map"] if g.gu_id == "GU-0001")
    assert gu.status == "resolved"
    assert gu.resolved_at is not None


def test_case_a_evidence_links_not_empty():
    """불변원칙 3: 신규 active KU는 evidence_links ≥ 1."""
    claim = _make_claim("GU-0001", _EK, "price", 50000, eu_id="EU-0010")
    state = _make_state(
        gap_map=[_make_gu("GU-0001", _EK, "price")],
        pending_claims=[claim],
    )
    result = integrate(state)
    active = next(k for k in result["knowledge_units"] if k.status == "active")
    assert len(active.evidence_links) >= 1
    assert "EU-0010" in active.evidence_links


# --- Case B: 같은 값 ---

def test_case_b_confidence_increases():
    """Case B: confidence +0.05."""
    existing = _make_ku("KU-0001", _EK, "price", 50000, confidence=0.8)
    claim = _make_claim("GU-0001", _EK, "price", 50000, eu_id="EU-0002")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    ku = next(k for k in result["knowledge_units"] if k.ku_id == "KU-0001")
    assert ku.confidence == pytest.approx(0.85)


def test_case_b_confidence_capped_at_1():
    """Case B: confidence는 1.0을 넘지 않는다."""
    existing = _make_ku("KU-0001", _EK, "price", 50000, confidence=0.98)
    claim = _make_claim("GU-0001", _EK, "price", 50000, eu_id="EU-0002")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    ku = next(k for k in result["knowledge_units"] if k.ku_id == "KU-0001")
    assert ku.confidence <= 1.0


def test_case_b_adds_eu_id():
    """Case B: eu_id가 evidence_links에 추가된다."""
    existing = _make_ku("KU-0001", _EK, "price", 50000, evidence_links=["EU-0001"])
    claim = _make_claim("GU-0001", _EK, "price", 50000, eu_id="EU-0002")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    ku = next(k for k in result["knowledge_units"] if k.ku_id == "KU-0001")
    assert "EU-0002" in ku.evidence_links


def test_case_b_no_duplicate_eu():
    """Case B: 이미 존재하는 eu_id는 중복 추가되지 않는다."""
    existing = _make_ku("KU-0001", _EK, "price", 50000, evidence_links=["EU-0001"])
    claim = _make_claim("GU-0001", _EK, "price", 50000, eu_id="EU-0001")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    ku = next(k for k in result["knowledge_units"] if k.ku_id == "KU-0001")
    assert ku.evidence_links.count("EU-0001") == 1


# --- Case C: 충돌 ---

def test_case_c_creates_conflicting_ku():
    """Case C: 다른 값 → conflicting KU 신규 생성."""
    existing = _make_ku("KU-0001", _EK, "price", 50000)
    claim = _make_claim("GU-0001", _EK, "price", 29650, eu_id="EU-0002")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    conflicting = [k for k in result["knowledge_units"] if k.status == "conflicting"]
    assert len(conflicting) == 1
    assert conflicting[0].value == 29650


def test_case_c_active_ku_value_unchanged():
    """Case C: active KU value 불변 (D4-A)."""
    existing = _make_ku("KU-0001", _EK, "price", 50000, confidence=0.9)
    claim = _make_claim("GU-0001", _EK, "price", 29650, eu_id="EU-0002")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    active = [k for k in result["knowledge_units"] if k.status == "active" and k.field == "price"]
    assert len(active) == 1
    assert active[0].value == 50000
    assert active[0].confidence == pytest.approx(0.9)


def test_case_c_conflicting_ku_has_evidence():
    """Case C: conflicting KU도 evidence_links를 가진다."""
    existing = _make_ku("KU-0001", _EK, "price", 50000)
    claim = _make_claim("GU-0001", _EK, "price", 29650, eu_id="EU-0099")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    conflicting = next(k for k in result["knowledge_units"] if k.status == "conflicting")
    assert "EU-0099" in conflicting.evidence_links


# --- 불변원칙 검증 ---

def test_invariant_2_single_active_ku_after_case_a():
    """불변원칙 2: Case A 후 (entity_key, field) active KU는 정확히 1개."""
    claim = _make_claim("GU-0001", _EK, "price", 50000)
    state = _make_state(
        gap_map=[_make_gu("GU-0001", _EK, "price")],
        pending_claims=[claim],
    )
    result = integrate(state)
    active = [
        k for k in result["knowledge_units"]
        if k.entity_key == _EK and k.field == "price" and k.status == "active"
    ]
    assert len(active) == 1


def test_invariant_2_case_c_preserves_single_active():
    """불변원칙 2: Case C 후에도 active KU는 정확히 1개."""
    existing = _make_ku("KU-0001", _EK, "price", 50000)
    claim = _make_claim("GU-0001", _EK, "price", 29650, eu_id="EU-0002")
    state = _make_state(knowledge_units=[existing], pending_claims=[claim])
    result = integrate(state)
    active = [
        k for k in result["knowledge_units"]
        if k.entity_key == _EK and k.field == "price" and k.status == "active"
    ]
    assert len(active) == 1


# --- pending_claims 정리 ---

def test_pending_claims_cleared_after_integrate():
    """integrate 완료 후 pending_claims는 비워진다."""
    claim = _make_claim("GU-0001", _EK, "price", 50000)
    state = _make_state(
        gap_map=[_make_gu("GU-0001", _EK, "price")],
        pending_claims=[claim],
    )
    result = integrate(state)
    assert result["pending_claims"] == []
