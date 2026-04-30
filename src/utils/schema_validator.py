from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError

SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"

_SCHEMA_FILES = {
    "ku": "knowledge-unit.json",
    "eu": "evidence-unit.json",
    "gu": "gap-unit.json",
    "domain-skeleton": "domain-skeleton.json",
    "entity-registry": "entity-registry.json",
}


@lru_cache(maxsize=8)
def _load_schema(kind: str) -> dict:
    path = SCHEMA_DIR / _SCHEMA_FILES[kind]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_validator(kind: str) -> Draft7Validator:
    return Draft7Validator(_load_schema(kind))


def validate_ku(ku: dict[str, Any]) -> list[ValidationError]:
    return list(_get_validator("ku").iter_errors(ku))


def validate_eu(eu: dict[str, Any]) -> list[ValidationError]:
    return list(_get_validator("eu").iter_errors(eu))


def validate_gu(gu: dict[str, Any]) -> list[ValidationError]:
    return list(_get_validator("gu").iter_errors(gu))


def validate_state(state: dict[str, Any]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for ku in state.get("knowledge_units", []):
        for err in validate_ku(ku):
            err.message = f"[{ku.get('ku_id', '?')}] {err.message}"
            errors.append(err)
    for gu in state.get("gap_map", []):
        for err in validate_gu(gu):
            err.message = f"[{gu.get('gu_id', '?')}] {err.message}"
            errors.append(err)
    return errors
