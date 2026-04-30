from __future__ import annotations

from unittest.mock import patch

from src.config import BronzeConfig
from src.nodes.critique import critique
from src.state import BronzeState, CategorySaturation, GU


MINI_SKELETON = {
    "domain": "test-d",
    "categories": [{"slug": "transport", "name": "교통"}],
    "fields": [],
}

_CONFIG = BronzeConfig(max_cycles=5)


def _make_saturation(is_saturated: bool) -> dict[str, CategorySaturation]:
    return {"transport": CategorySaturation(is_saturated=is_saturated)}


def _make_gu(gu_id: str, status: str = "open") -> GU:
    return GU(
        gu_id=gu_id,
        entity_key="test-d:transport:jr-pass",
        field="price",
        status=status,
        created_at="2026-01-01T00:00:00+00:00",
    )


def _make_state(
    current_cycle: int = 0,
    category_saturation: dict | None = None,
    gap_map: list[GU] | None = None,
) -> BronzeState:
    return BronzeState(
        domain_skeleton=MINI_SKELETON,
        current_cycle=current_cycle,
        category_saturation=category_saturation if category_saturation is not None else {},
        gap_map=gap_map or [],
    )


def _run(state: BronzeState, config: BronzeConfig = _CONFIG) -> dict:
    with patch("src.nodes.critique.BronzeConfig.from_env", return_value=config):
        return critique(state)


# --- 수렴 ---

def test_converged_when_all_saturated_and_no_open_gus():
    """all_saturated=True AND open GU 없음 → terminate_reason='converged'."""
    state = _make_state(
        category_saturation=_make_saturation(True),
        gap_map=[_make_gu("GU-0001", status="resolved")],
    )
    result = _run(state)
    assert result["terminate_reason"] == "converged"


def test_not_converged_when_open_gus_remain():
    """open GU가 있으면 수렴하지 않는다."""
    state = _make_state(
        category_saturation=_make_saturation(True),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert result["terminate_reason"] != "converged"


def test_not_converged_when_not_all_saturated():
    """카테고리 포화 안 됐으면 open GU 없어도 수렴하지 않는다."""
    state = _make_state(
        category_saturation=_make_saturation(False),
        gap_map=[],
    )
    result = _run(state)
    assert result["terminate_reason"] != "converged"


def test_converged_priority_over_max_cycles():
    """수렴 조건과 max_cycles 동시 충족 시 converged 우선 (§C.5 순서)."""
    state = _make_state(
        current_cycle=5,
        category_saturation=_make_saturation(True),
        gap_map=[],
    )
    result = _run(state)
    assert result["terminate_reason"] == "converged"


# --- 강제종료 ---

def test_max_cycles_exact_terminates():
    """current_cycle == max_cycles → terminate_reason='max_cycles'."""
    state = _make_state(
        current_cycle=5,
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert result["terminate_reason"] == "max_cycles"


def test_max_cycles_exceeded_terminates():
    """current_cycle > max_cycles도 강제종료."""
    state = _make_state(
        current_cycle=10,
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert result["terminate_reason"] == "max_cycles"


# --- 계속 ---

def test_continue_increments_current_cycle():
    """계속 조건: current_cycle += 1."""
    state = _make_state(
        current_cycle=2,
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert result["current_cycle"] == 3


def test_continue_no_terminate_reason():
    """계속 조건: terminate_reason=None."""
    state = _make_state(
        current_cycle=0,
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert result["terminate_reason"] is None


def test_terminate_does_not_include_current_cycle():
    """종료(max_cycles) 시 current_cycle을 반환하지 않는다."""
    state = _make_state(
        current_cycle=5,
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert result["terminate_reason"] == "max_cycles"
    assert "current_cycle" not in result


# --- metrics ---

def test_metrics_returned_on_continue():
    """계속 시 metrics 3개 포함."""
    state = _make_state(
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert "metrics" in result
    assert "gap_resolution_rate" in result["metrics"]
    assert "avg_confidence" in result["metrics"]
    assert "evidence_rate" in result["metrics"]


def test_metrics_returned_on_terminate():
    """종료 시에도 metrics 포함."""
    state = _make_state(
        current_cycle=5,
        category_saturation=_make_saturation(False),
        gap_map=[_make_gu("GU-0001", status="open")],
    )
    result = _run(state)
    assert "metrics" in result
