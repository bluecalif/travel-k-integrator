from __future__ import annotations

from src.state import BronzeState


def gap_resolution_rate(state: BronzeState) -> float:
    """resolved / (resolved + open + failed). failed 포함 분모."""
    resolved = sum(1 for gu in state.gap_map if gu.status == "resolved")
    total = len(state.gap_map)
    if total == 0:
        return 0.0
    return resolved / total


def avg_confidence(state: BronzeState) -> float:
    """active KU의 평균 confidence."""
    active = [ku for ku in state.knowledge_units if ku.status == "active"]
    if not active:
        return 0.0
    return sum(ku.confidence for ku in active) / len(active)


def evidence_rate(state: BronzeState) -> float:
    """active KU 중 evidence_links 비어있지 않은 비율.

    불변원칙 3에 의해 항상 1.0이어야 함.
    """
    active = [ku for ku in state.knowledge_units if ku.status == "active"]
    if not active:
        return 0.0
    return sum(1 for ku in active if ku.evidence_links) / len(active)


def compute_metrics(state: BronzeState) -> dict:
    return {
        "gap_resolution_rate": gap_resolution_rate(state),
        "avg_confidence": avg_confidence(state),
        "evidence_rate": evidence_rate(state),
    }
