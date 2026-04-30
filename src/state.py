from dataclasses import dataclass, field
from typing import Literal


@dataclass
class EntityMeta:
    category: str
    name: str
    registered_at: str
    source: Literal["seed", "entity_gen"]
    cycle: int | None = None


@dataclass
class KU:
    ku_id: str
    entity_key: str
    field: str
    value: object
    confidence: float
    status: Literal["active", "conflicting", "archived"]
    evidence_links: list[str]
    created_at: str
    updated_at: str


@dataclass
class EU:
    eu_id: str
    url: str
    title: str
    snippet: str
    retrieved_at: str
    search_query: str


@dataclass
class GU:
    gu_id: str
    entity_key: str
    field: str
    status: Literal["open", "resolved", "failed"]
    created_at: str
    resolved_at: str | None = None
    attempts: int = 0


@dataclass
class CategorySaturation:
    is_saturated: bool = False
    consecutive_failures: int = 0


@dataclass
class BronzeState:
    domain_skeleton: dict
    entity_registry: dict[str, EntityMeta]             = field(default_factory=dict)
    knowledge_units: list[KU]                          = field(default_factory=list)
    evidence_units: list[EU]                           = field(default_factory=list)
    gap_map: list[GU]                                  = field(default_factory=list)
    category_saturation: dict[str, CategorySaturation] = field(default_factory=dict)
    target_entities: dict[str, str]                     = field(default_factory=dict)
    current_cycle: int                                 = 0
    plan_queue: list[str]                              = field(default_factory=list)
    pending_claims: list[dict]                         = field(default_factory=list)
    metrics: dict                                      = field(default_factory=dict)
    terminate_reason: str | None                       = None
