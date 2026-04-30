from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BronzeConfig:
    openai_api_key: str = ""
    tavily_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    max_gus_per_cycle: int = 25
    max_search_calls_per_cycle: int = 25
    max_entities_per_category: int = 20
    similarity_threshold: float = 0.85
    saturation_consecutive_threshold: int = 2
    gu_max_attempts: int = 3
    budget_cap_usd: float = 1.2

    @classmethod
    def from_env(cls) -> BronzeConfig:
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
            llm_model=os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
            llm_temperature=float(os.environ.get("LLM_TEMPERATURE", "0.0")),
            llm_max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "1024")),
            max_gus_per_cycle=int(os.environ.get("BRONZE_MAX_GUS_PER_CYCLE", "25")),
            max_search_calls_per_cycle=int(os.environ.get("BRONZE_MAX_SEARCH_CALLS_PER_CYCLE", "25")),
            max_entities_per_category=int(os.environ.get("BRONZE_MAX_ENTITIES_PER_CATEGORY", "20")),
            similarity_threshold=float(os.environ.get("BRONZE_SIMILARITY_THRESHOLD", "0.85")),
            saturation_consecutive_threshold=int(os.environ.get("BRONZE_SATURATION_CONSECUTIVE_THRESHOLD", "2")),
            gu_max_attempts=int(os.environ.get("BRONZE_GU_MAX_ATTEMPTS", "3")),
            budget_cap_usd=float(os.environ.get("BRONZE_BUDGET_CAP_USD", "1.2")),
        )

    def validate_api_keys(self) -> None:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY가 설정되지 않았습니다.")

    def redact(self) -> dict:
        d = dataclasses.asdict(self)
        for key in ("openai_api_key", "tavily_api_key"):
            d[key] = "<redacted>" if d[key] else ""
        return d


def _get_git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, timeout=5
        )
        return out.decode("utf-8").strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"


def write_config_snapshot(
    config: BronzeConfig,
    trial_dir: Path | str,
    *,
    skeleton_path: Path | str | None = None,
) -> Path:
    trial_dir = Path(trial_dir)
    trial_dir.mkdir(parents=True, exist_ok=True)

    if skeleton_path is None:
        candidate = trial_dir / "state" / "domain-skeleton.json"
        skeleton_path = candidate if candidate.exists() else None
    else:
        skeleton_path = Path(skeleton_path)

    if skeleton_path is not None and skeleton_path.exists():
        skeleton_sha256 = hashlib.sha256(skeleton_path.read_bytes()).hexdigest()
        skeleton_ref = str(skeleton_path)
    else:
        skeleton_sha256 = "missing"
        skeleton_ref = str(skeleton_path) if skeleton_path is not None else ""

    snapshot = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_head": _get_git_head(),
        "config": config.redact(),
        "skeleton_path": skeleton_ref,
        "skeleton_sha256": skeleton_sha256,
    }

    target = trial_dir / "config.snapshot.json"
    target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("config snapshot 기록: %s", target)
    return target
