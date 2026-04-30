from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.adapters.llm_adapter import create_llm
from src.adapters.search_adapter import TavilySearchAdapter
from src.config import BronzeConfig
from src.state import BronzeState, EU
from src.utils.llm_parse import extract_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_claim_from_snippet(
    entity_key: str,
    field: str,
    snippet: str,
    eu_id: str,
    gu_id: str,
    llm: Any,
) -> dict | None:
    prompt = (
        f"다음 snippet에서 (entity={entity_key}, field={field}) 에 대한 사실 주장을 추출.\n"
        f'snippet: "{snippet}"\n\n'
        '응답 (JSON):\n{"value": <string|object>, "confidence": <0.0~1.0>}\n\n'
        "사실 주장이 명확하지 않으면 null."
    )
    response = llm.invoke(prompt)
    text = response.content.strip()
    if text.lower() == "null":
        return None
    try:
        parsed = extract_json(text)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    if "value" not in parsed or "confidence" not in parsed:
        return None
    return {
        "gu_id": gu_id,
        "entity_key": entity_key,
        "field": field,
        "value": parsed["value"],
        "confidence": float(parsed["confidence"]),
        "eu_id": eu_id,
    }


def collect(state: BronzeState) -> dict:
    """plan_queue 각 GU → Tavily 검색 → EU 생성 → LLM Claim 추출 → pending_claims 누적.

    EU는 claim 추출 실패해도 생성됨 (evidence-first).
    0-claim GU: attempts++. attempts >= gu_max_attempts → status="failed".
    open 상태가 아닌 GU는 처리 건너뜀.
    """
    config = BronzeConfig.from_env()
    llm = create_llm(config)
    search = TavilySearchAdapter(config)

    gap_map = list(state.gap_map)
    gu_by_id = {g.gu_id: g for g in gap_map}

    evidence_units = list(state.evidence_units)
    pending_claims = list(state.pending_claims)
    now = _now_iso()

    for gu_id in state.plan_queue:
        gu = gu_by_id.get(gu_id)
        if gu is None or gu.status != "open":
            continue

        entity_key = gu.entity_key
        field = gu.field
        meta = state.entity_registry.get(entity_key)
        entity_name = meta.name if meta else entity_key.split(":")[-1].replace("-", " ")
        query = f"{entity_name} {field}"

        results = search.search(query)

        claims_for_gu: list[dict] = []
        for r in results:
            eu_id = f"EU-{len(evidence_units) + 1:04d}"
            evidence_units.append(EU(
                eu_id=eu_id,
                url=r.get("url", ""),
                title=r.get("title", ""),
                snippet=r.get("snippet", ""),
                retrieved_at=now,
                search_query=query,
            ))

            snippet = r.get("snippet", "")
            if not snippet:
                continue

            claim = _extract_claim_from_snippet(entity_key, field, snippet, eu_id, gu_id, llm)
            if claim:
                pending_claims.append(claim)
                claims_for_gu.append(claim)

        if not claims_for_gu:
            gu.attempts += 1
            if gu.attempts >= config.gu_max_attempts:
                gu.status = "failed"

    return {
        "evidence_units": evidence_units,
        "pending_claims": pending_claims,
        "gap_map": gap_map,
    }
