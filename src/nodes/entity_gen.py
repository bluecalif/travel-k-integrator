from __future__ import annotations

from datetime import datetime, timezone

from src.adapters.llm_adapter import create_llm
from src.config import BronzeConfig
from src.nodes.seed import _resolve_applicable_fields
from src.state import BronzeState, EntityMeta, GU
from src.utils.entity_resolver import extract_slug, max_similarity
from src.utils.llm_parse import extract_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _llm_generate_candidate(
    domain: str,
    category: str,
    existing_slugs: list[str],
    all_entity_names: list[str],
    llm: object,
) -> dict | None:
    existing_str = ", ".join(existing_slugs) if existing_slugs else "(없음)"
    all_names_str = ", ".join(all_entity_names) if all_entity_names else "(없음)"
    prompt = (
        f"도메인: {domain}\n"
        f"카테고리: {category}\n"
        f"이 카테고리의 기존 entity: {existing_str}\n"
        f"전체 레지스트리 entity (모든 카테고리): {all_names_str}\n\n"
        "위 카테고리에 추가할 만한 새 entity 1개를 제안하시오.\n"
        '형식: {"slug": "...", "name": "..."}\n'
        "조건:\n"
        '- slug는 영문 소문자 + 하이픈 (예: "jr-pass")\n'
        "- 이 카테고리의 기존 entity와 명확히 구별되는 별개 entity\n"
        "- 전체 레지스트리에 이미 있는 entity를 다른 카테고리에 재등록하지 말 것\n"
        "- 일반 여행자가 검색할 만한 구체적 실명 entity (브랜드명·장소명·서비스명)\n"
        "- 추상적 카테고리명·음식 종류·교통수단 종류 등 상위 개념은 사용 금지\n"
        "적절한 후보가 없으면 null."
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
    if "slug" not in parsed or "name" not in parsed:
        return None
    slug = str(parsed["slug"]).strip().lower()
    if not slug:
        return None
    return {"slug": slug, "name": parsed["name"]}


def entity_gen(state: BronzeState) -> dict:
    """비포화 카테고리별 LLM entity 후보 1개 생성·등록.

    de-dup (카테고리): max_similarity(candidate, cat_slugs) >= threshold → 거부.
    de-dup (전역): max_similarity(candidate, all_slugs) >= threshold → 거부.
    연속 saturation_consecutive_threshold 회 실패 → is_saturated = True.
    """
    config = BronzeConfig.from_env()
    llm = create_llm(config)

    skeleton = state.domain_skeleton
    domain = skeleton["domain"]
    categories = [cat["slug"] for cat in skeleton.get("categories", [])]

    entity_registry = dict(state.entity_registry)
    gap_map = list(state.gap_map)
    category_saturation = state.category_saturation  # mutate in-place

    for cat in categories:
        sat = category_saturation.get(cat)
        if sat is None or sat.is_saturated:
            continue

        existing_in_cat = [
            ek for ek, meta in entity_registry.items()
            if meta.category == cat
        ]
        existing_slugs = [extract_slug(ek) for ek in existing_in_cat]
        all_entity_names = [meta.name for meta in entity_registry.values()]

        candidate = _llm_generate_candidate(domain, cat, existing_slugs, all_entity_names, llm)

        if candidate is None:
            sat.consecutive_failures += 1
            if sat.consecutive_failures >= config.saturation_consecutive_threshold:
                sat.is_saturated = True
            continue

        # 카테고리 내 de-dup
        cat_sim = max_similarity(candidate["slug"], existing_slugs)
        if cat_sim >= config.similarity_threshold:
            sat.consecutive_failures += 1
            if sat.consecutive_failures >= config.saturation_consecutive_threshold:
                sat.is_saturated = True
            continue

        # 전역 de-dup: 모든 카테고리 slug와 비교
        all_slugs = [extract_slug(ek) for ek in entity_registry.keys()]
        global_sim = max_similarity(candidate["slug"], all_slugs)
        if global_sim >= config.similarity_threshold:
            sat.consecutive_failures += 1
            if sat.consecutive_failures >= config.saturation_consecutive_threshold:
                sat.is_saturated = True
            continue

        if len(existing_in_cat) >= config.max_entities_per_category:
            sat.is_saturated = True
            continue

        sat.consecutive_failures = 0
        now = _now_iso()
        entity_key = f"{domain}:{cat}:{candidate['slug']}"
        entity_registry[entity_key] = EntityMeta(
            category=cat,
            name=candidate["name"],
            registered_at=now,
            source="entity_gen",
            cycle=state.current_cycle,
        )

        applicable = _resolve_applicable_fields(cat, skeleton)
        for f in applicable:
            gap_map.append(GU(
                gu_id=f"GU-{len(gap_map) + 1:04d}",
                entity_key=entity_key,
                field=f,
                status="open",
                created_at=now,
            ))

    return {
        "entity_registry": entity_registry,
        "gap_map": gap_map,
        "category_saturation": category_saturation,
    }
