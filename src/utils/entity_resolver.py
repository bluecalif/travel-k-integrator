from __future__ import annotations

import difflib


def slug_similarity(slug_a: str, slug_b: str) -> float:
    """두 slug 간 유사도 (0.0 ~ 1.0). difflib.SequenceMatcher 기반."""
    return difflib.SequenceMatcher(None, slug_a, slug_b).ratio()


def max_similarity(candidate_slug: str, existing_slugs: list[str]) -> float:
    """candidate_slug과 기존 slug 목록 중 최대 유사도 반환."""
    if not existing_slugs:
        return 0.0
    return max(slug_similarity(candidate_slug, s) for s in existing_slugs)


def canonicalize_entity_key(entity_key: str) -> str:
    """entity_key를 canonical 형태로 정규화.

    lowercase + strip + 공백 → 하이픈. idempotent.
    """
    return entity_key.strip().lower().replace(" ", "-")


def extract_slug(entity_key: str) -> str:
    """entity_key에서 slug 부분 추출 ({domain}:{category}:{slug})."""
    parts = entity_key.split(":")
    return parts[-1] if parts else entity_key
