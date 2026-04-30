from __future__ import annotations

import re
from datetime import datetime, timezone

from src.state import BronzeState, KU


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_numeric_str(s: str) -> str:
    """숫자 표기 정규화: 통화기호/쉼표/공백 제거."""
    s = re.sub(r'[¥$€£₩]', '', s)
    s = re.sub(r'\b(JPY|USD|EUR|KRW|GBP)\b', '', s, flags=re.IGNORECASE)
    return s.replace(',', '').strip()


def _same_value(a: object, b: object) -> bool:
    """두 값이 동일한지 판단 — 정확 일치 또는 숫자 표기 정규화 후 일치.

    Bronze에서는 정확 일치 + 숫자 정규화만 사용 ("50,000" ↔ 50000).
    의미적 동치 LLM 비교는 Silver 이후.
    """
    if a == b:
        return True
    a_norm = _normalize_numeric_str(str(a))
    b_norm = _normalize_numeric_str(str(b))
    return a_norm == b_norm


def _find_active_ku(knowledge_units: list[KU], entity_key: str, field: str) -> KU | None:
    for ku in knowledge_units:
        if ku.entity_key == entity_key and ku.field == field and ku.status == "active":
            return ku
    return None


def _next_ku_id(knowledge_units: list[KU]) -> str:
    max_n = 0
    for ku in knowledge_units:
        if ku.ku_id.startswith("KU-"):
            try:
                max_n = max(max_n, int(ku.ku_id[3:]))
            except ValueError:
                pass
    return f"KU-{max_n + 1:04d}"


def integrate(state: BronzeState) -> dict:
    """pending_claims → KU/GU 통합.

    Case A: active KU 없음 → 신규 KU(active) 생성 + GU resolved
    Case B: active KU 있고 같은 값 → evidence_links 추가, confidence +0.05 (max 1.0)
    Case C: active KU 있고 다른 값 → conflicting KU 신규 생성 (active KU 불변, D4-A)
    resolve_gu는 Case A에서만.
    """
    knowledge_units = list(state.knowledge_units)
    gap_map = list(state.gap_map)
    gu_by_id = {g.gu_id: g for g in gap_map}
    now = _now_iso()

    for claim in state.pending_claims:
        entity_key = claim["entity_key"]
        field = claim["field"]
        value = claim["value"]
        confidence = float(claim["confidence"])
        eu_id = claim["eu_id"]
        gu_id = claim["gu_id"]

        active_ku = _find_active_ku(knowledge_units, entity_key, field)

        if active_ku is None:
            # Case A: 신규 KU active 생성 + GU resolved
            new_ku = KU(
                ku_id=_next_ku_id(knowledge_units),
                entity_key=entity_key,
                field=field,
                value=value,
                confidence=confidence,
                status="active",
                evidence_links=[eu_id],
                created_at=now,
                updated_at=now,
            )
            knowledge_units.append(new_ku)

            gu = gu_by_id.get(gu_id)
            if gu is not None and gu.status == "open":
                gu.status = "resolved"
                gu.resolved_at = now

        elif _same_value(active_ku.value, value):
            # Case B: 같은 값 → evidence 보강
            if eu_id not in active_ku.evidence_links:
                active_ku.evidence_links.append(eu_id)
            active_ku.confidence = min(1.0, active_ku.confidence + 0.05)
            active_ku.updated_at = now

        else:
            # Case C: 다른 값 → conflicting KU 신규 생성 (active KU 불변, D4-A)
            conflicting_ku = KU(
                ku_id=_next_ku_id(knowledge_units),
                entity_key=entity_key,
                field=field,
                value=value,
                confidence=confidence,
                status="conflicting",
                evidence_links=[eu_id],
                created_at=now,
                updated_at=now,
            )
            knowledge_units.append(conflicting_ku)

    return {
        "knowledge_units": knowledge_units,
        "gap_map": gap_map,
        "pending_claims": [],
    }
