from __future__ import annotations

from dataclasses import dataclass, field

from src.state import BronzeState


@dataclass
class InvariantResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


def check_evidence_first(state: BronzeState) -> list[str]:
    """불변원칙 3: active KU 중 evidence_links=[] 인 것 반환."""
    return [
        ku.ku_id
        for ku in state.knowledge_units
        if ku.status == "active" and not ku.evidence_links
    ]


def check_active_ku_uniqueness(state: BronzeState) -> list[str]:
    """불변원칙 2: (entity_key, field) 조합에 active KU 2개 이상인 것 반환."""
    seen: dict[tuple[str, str], int] = {}
    for ku in state.knowledge_units:
        if ku.status == "active":
            key = (ku.entity_key, ku.field)
            seen[key] = seen.get(key, 0) + 1
    return [f"{ek}:{f}" for (ek, f), cnt in seen.items() if cnt > 1]


def check_gap_driven(state: BronzeState) -> list[str]:
    """불변원칙 1: resolved GU 없이 생성된 active KU 탐지.

    active KU의 (entity_key, field)에 대응하는 resolved GU가 없으면 위반.
    """
    resolved_pairs = {
        (gu.entity_key, gu.field)
        for gu in state.gap_map
        if gu.status == "resolved"
    }
    return [
        ku.ku_id
        for ku in state.knowledge_units
        if ku.status == "active" and (ku.entity_key, ku.field) not in resolved_pairs
    ]


def check_conflict_preserving(state: BronzeState) -> list[str]:
    """불변원칙 4: 동일 (entity_key, field)에 active KU가 2개 이상인 경우 감지.

    conflicting 값이 active로 덮어써진 상황 (한 쌍에 active 2개 이상).
    """
    return check_active_ku_uniqueness(state)


def check_invariants(state: BronzeState) -> InvariantResult:
    """4대 불변원칙 일괄 검증."""
    violations: list[str] = []

    for ku_id in check_evidence_first(state):
        violations.append(f"[I3] Evidence-first 위반: {ku_id} — evidence_links 비어있음")

    for pair in check_active_ku_uniqueness(state):
        violations.append(f"[I2] active KU 중복: {pair}")

    for ku_id in check_gap_driven(state):
        violations.append(f"[I1] Gap-driven 위반: {ku_id} — resolved GU 없음")

    return InvariantResult(passed=len(violations) == 0, violations=violations)
