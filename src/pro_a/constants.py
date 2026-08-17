NODE_TYPES = [
    "Industry", "Segment", "Technology", "Product", "Material", "Equipment",
    "Entity", "Application", "Standard", "Policy", "Theme", "Event", "ResearchQuestion",
]

RELATION_TYPES = [
    "part_of", "upstream_of", "supplies", "produces", "uses", "applied_in",
    "substitutes", "depends_on", "constrains", "drives", "competes_with",
    "benefits_from", "exposed_to", "regulated_by", "validates", "invalidates", "related_to",
]

CLAIM_NATURES = [
    "fact", "data", "company_guidance", "expert_judgment", "broker_forecast",
    "market_rumor", "user_judgment", "ai_inference",
]

CLAIM_STATUSES = ["current", "pending_verification", "updated", "invalidated", "expired", "disputed", "needs_review"]
NOVELTY_LEVELS = ["N0", "N1", "N2", "N3"]

CHANGE_LEVELS = ["initial", "minor", "material", "thesis"]

PROPOSAL_TYPES = ["new_node", "current_view_change", "node_relation"]
PROPOSAL_STATUSES = ["pending", "accepted", "rejected", "modified", "stale"]

INGESTION_MODES = ["archive", "standard", "deep"]

SOURCE_RANKS = ["S", "A", "B", "C", "D", "UNRANKED"]
SOURCE_ORIGIN_TYPES = ["primary", "secondary", "unknown"]

GAP_STATUSES = ["open", "resolved", "no_longer_relevant", "superseded", "reopened", "needs_refresh"]
RQ_STATUSES = ["open", "resolved", "dormant", "obsolete", "reopened"]

STRUCTURAL_RELATIONS = {"part_of"}
