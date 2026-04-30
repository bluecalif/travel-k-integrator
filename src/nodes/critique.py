from __future__ import annotations

from src.config import BronzeConfig
from src.state import BronzeState
from src.utils.metrics import compute_metrics


def critique(state: BronzeState) -> dict:
    """수렴/강제종료 판정 + metrics 업데이트.

    수렴: all_saturated AND open GU 없음 → terminate_reason="converged"
    강제종료: current_cycle >= max_cycles → terminate_reason="max_cycles"
    계속: terminate_reason=None, current_cycle += 1

    prescription 생성 로직 없음 (D11). 수렴/강제종료 판정만.
    """
    config = BronzeConfig.from_env()

    all_saturated = all(s.is_saturated for s in state.category_saturation.values())
    open_count = sum(1 for g in state.gap_map if g.status == "open")
    metrics = compute_metrics(state)

    if all_saturated and open_count == 0:
        return {
            "terminate_reason": "converged",
            "metrics": metrics,
        }

    if state.current_cycle >= config.max_cycles:
        return {
            "terminate_reason": "max_cycles",
            "metrics": metrics,
        }

    return {
        "terminate_reason": None,
        "current_cycle": state.current_cycle + 1,
        "metrics": metrics,
    }
