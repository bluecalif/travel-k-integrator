from __future__ import annotations

import dataclasses
import json
import logging
import shutil
from pathlib import Path

from src.state import BronzeState, CategorySaturation, EU, EntityMeta, GU, KU

logger = logging.getLogger(__name__)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _read_json(path: Path) -> object:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: BronzeState, trial_dir: str | Path) -> None:
    state_dir = Path(trial_dir) / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    _write_json(state_dir / "domain-skeleton.json", state.domain_skeleton)
    _write_json(
        state_dir / "entity-registry.json",
        {k: dataclasses.asdict(v) for k, v in state.entity_registry.items()},
    )
    _write_json(state_dir / "knowledge-units.json", [dataclasses.asdict(ku) for ku in state.knowledge_units])
    _write_json(state_dir / "evidence-units.json", [dataclasses.asdict(eu) for eu in state.evidence_units])
    _write_json(state_dir / "gap-map.json", [dataclasses.asdict(gu) for gu in state.gap_map])
    _write_json(state_dir / "metrics.json", state.metrics)
    _write_json(state_dir / "category-saturation.json", {
        k: dataclasses.asdict(v) for k, v in state.category_saturation.items()
    })
    _write_json(state_dir / "run-meta.json", {
        "target_entities": state.target_entities,
        "current_cycle": state.current_cycle,
        "plan_queue": state.plan_queue,
        "pending_claims": state.pending_claims,
        "terminate_reason": state.terminate_reason,
    })


def load_state(trial_dir: str | Path) -> BronzeState:
    state_dir = Path(trial_dir) / "state"

    skeleton = _read_json(state_dir / "domain-skeleton.json")

    reg_raw = _read_json(state_dir / "entity-registry.json")
    entity_registry = {k: EntityMeta(**v) for k, v in reg_raw.items()}

    kus_raw = _read_json(state_dir / "knowledge-units.json")
    knowledge_units = [KU(**d) for d in kus_raw]

    eus_raw = _read_json(state_dir / "evidence-units.json")
    evidence_units = [EU(**d) for d in eus_raw]

    gus_raw = _read_json(state_dir / "gap-map.json")
    gap_map = [GU(**d) for d in gus_raw]

    metrics = _read_json(state_dir / "metrics.json")

    sat_raw = _read_json(state_dir / "category-saturation.json")
    category_saturation = {k: CategorySaturation(**v) for k, v in sat_raw.items()}

    meta = _read_json(state_dir / "run-meta.json")

    return BronzeState(
        domain_skeleton=skeleton,
        entity_registry=entity_registry,
        knowledge_units=knowledge_units,
        evidence_units=evidence_units,
        gap_map=gap_map,
        metrics=metrics,
        category_saturation=category_saturation,
        target_entities=meta.get("target_entities", {}),
        current_cycle=meta.get("current_cycle", 0),
        plan_queue=meta.get("plan_queue", []),
        pending_claims=meta.get("pending_claims", []),
        terminate_reason=meta.get("terminate_reason"),
    )


def snapshot_state(trial_dir: str | Path, cycle: int) -> Path:
    trial_dir = Path(trial_dir)
    state_dir = trial_dir / "state"
    snapshot_dir = trial_dir / "state-snapshots" / f"cycle-{cycle}-snapshot"

    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    shutil.copytree(state_dir, snapshot_dir)
    logger.info("snapshot saved: cycle %d → %s", cycle, snapshot_dir)
    return snapshot_dir
