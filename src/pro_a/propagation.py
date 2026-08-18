from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from .analyzer import Analyzer, attribution_subjects, canonicalize_text
from .config import AppConfig
from .db import CURRENT_VIEW_ORDER, Database, now_iso
from .ids import make_id
from .receipts import write_proposal


NO_TARGET_VIEW = "<none>"
HIGH_PRIMARY_RANKS = {"S", "A"}
MATERIAL_QUALITY_RANKS = {"S", "A", "B"}
THESIS_QUALITY_RANKS = {"S", "A"}
JUDGMENT_NATURES = {
    "company_guidance", "expert_judgment", "broker_forecast", "market_rumor",
    "user_judgment", "ai_inference",
}
KEY_FACT_NATURES = {"fact", "data", "company_guidance"}
NON_ENTITY_SCOPE_TYPES = {
    "Industry", "Segment", "Technology", "Product", "Material", "Equipment",
    "Application", "Theme",
}
PRODUCT_TYPE_FIELDS = {
    "applications", "demand_drivers", "supply_capacity", "pricing",
    "major_suppliers", "product_evolution",
}
APPLICATION_RELATION_CUES = ("用于", "应用于", "下游为", "下游包括", "应用", "application")
SUPPLIER_IDENTITY_CUES = ("供应商", "原厂", "厂商", "生产商", "制造商", "供货商")
SUPPLIER_STRENGTH_CUES = ("主要", "核心", "头部", "领先", "龙头", "最大", "关键")
SUPPLY_CAPACITY_CUES = ("产能", "出货量", "满产", "量产", "达产", "爬坡", "扩产", "投资")
FUTURE_CLAIM_NATURES = {"company_guidance", "broker_forecast"}
FUTURE_SEMANTIC_RE = re.compile(
    r"预计|预期|计划|目标|有望|指引|展望|未来|届时|拟|将(?!近)"
)
NUMBER_TOKEN_RE = re.compile(
    r"\d+(?:\.\d+)?(?:\s*(?:Q[1-4]|H[12]|M\d{1,2}|年(?:底|末)?|月|日|"
    r"亿颗(?:/月)?|亿元|亿|万|%|倍))?",
    re.IGNORECASE,
)
CAUSAL_CUES = (
    "导致", "引发", "使得", "使", "造成", "从而", "进而", "带来", "推动", "驱动",
)
TREND_CUES = (
    "价格战", "竞争加剧", "扩产加剧", "供给过剩", "供需改善", "需求增长",
    "需求下滑", "上行周期", "下行周期", "涨价趋势", "降价趋势",
)
TREND_QUALIFIERS = (
    "待验证", "尚待", "不能确认", "无法确认", "不足以", "是否", "跟踪", "关注",
    "可能", "或", "风险",
)
ORG_NAME_RE = re.compile(
    r"(?:^|[，,。；;：:\s（(])"
    r"([\u4e00-\u9fff]{2,8}(?:科技|电子|电机|集团|股份|半导体|材料|精密|控股|实业))"
)
ATOMIC_FUTURE_FIELDS = {
    "key_facts",
    "type_specific.supply_capacity",
    "type_specific.pricing",
    "type_specific.product_evolution",
}


class CurrentViewValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class PropagationManager:
    def __init__(self, cfg: AppConfig, db: Database, analyzer: Analyzer):
        self.cfg = cfg
        self.db = db
        self.analyzer = analyzer

    def _claims(self, claim_ids: list[str]) -> list[dict[str, Any]]:
        if not claim_ids:
            return []
        placeholders = ",".join("?" for _ in claim_ids)
        return self.db.all(
            f"""SELECT c.*,s.source_rank,s.origin_type,s.source_id AS evidence_source_id,
                s.underlying_source_id FROM claims c JOIN sources s ON s.source_id=c.source_id
                WHERE c.claim_id IN ({placeholders})""",
            claim_ids,
        )

    @staticmethod
    def _independence_key(claim: dict[str, Any]) -> str:
        return claim.get("underlying_source_id") or claim.get("evidence_source_id") or claim.get("source_id") or ""

    def _evidence_profile(self, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        sources: dict[str, dict[str, Any]] = {}
        independent: set[str] = set()
        for item in evidence:
            if not item.get("claim_id"):
                continue
            source_id = item.get("evidence_source_id") or item.get("source_id") or ""
            if source_id:
                sources.setdefault(source_id, item)
            key = self._independence_key(item)
            if key:
                independent.add(key)

        def distribution(field: str, default: str) -> dict[str, int]:
            counts: dict[str, int] = {}
            for source_id in sorted(sources):
                value = str(sources[source_id].get(field) or default)
                counts[value] = counts.get(value, 0) + 1
            return dict(sorted(counts.items()))

        companies = {
            company for item in evidence if (company := self._company_subject(item))
        }
        evidence_scope = (
            "multi_company_sample"
            if len(companies) >= 2 and len(independent) >= 2
            else "single_company_sample" if companies else "industry_level"
        )
        return {
            "evidence_source_count": len(sources),
            "independent_evidence_source_count": len(independent),
            "source_rank_distribution": distribution("source_rank", "UNRANKED"),
            "source_origin_distribution": distribution("origin_type", "unknown"),
            "evidence_scope": evidence_scope,
        }

    @staticmethod
    def _structured(claim: dict[str, Any]) -> dict[str, Any]:
        value = claim.get("structured_json") or {}
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}

    def _company_subject(self, claim: dict[str, Any]) -> str:
        structured_company = canonicalize_text(str(self._structured(claim).get("company") or ""))
        if structured_company:
            return structured_company
        scope = canonicalize_text(str(claim.get("scope") or ""))
        if claim.get("nature") == "company_guidance" or "公司" in scope or "企业" in scope:
            subjects = attribution_subjects(str(claim.get("attributed_to") or ""))
            return subjects[-1] if subjects else ""
        return ""

    @staticmethod
    def _claim_refs(text: str, by_id: dict[str, dict[str, Any]]) -> list[str]:
        return [claim_id for claim_id in by_id if claim_id in text]

    @staticmethod
    def _item_text(item: Any) -> str:
        return item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)

    @classmethod
    def _evidence_bearing_items(
        cls, proposed: dict[str, Any]
    ) -> list[tuple[str, int | None, str]]:
        items: list[tuple[str, int | None, str]] = []
        for field in ("one_line_conclusion", "investment_implication"):
            value = proposed.get(field)
            if isinstance(value, str):
                items.append((field, None, value))
        for field in ("core_logic", "key_facts", "major_risks"):
            for index, item in enumerate(proposed.get(field) or []):
                if isinstance(item, (str, dict)):
                    items.append((field, index, cls._item_text(item)))
        type_specific = proposed.get("type_specific") or {}
        if isinstance(type_specific, dict):
            for field, values in type_specific.items():
                if not isinstance(values, list):
                    continue
                for index, item in enumerate(values):
                    if isinstance(item, (str, dict)):
                        items.append(
                            (f"type_specific.{field}", index, cls._item_text(item))
                        )
        return items

    @staticmethod
    def _field_label(field: str, index: int | None) -> str:
        return field if index is None else f"{field}[{index}]"

    @staticmethod
    def _number_tokens(text: str, claim_ids: list[str]) -> set[str]:
        for claim_id in claim_ids:
            text = text.replace(claim_id, "")
        return {
            re.sub(r"\s+", "", match.group(0)).lower()
            for match in NUMBER_TOKEN_RE.finditer(text)
        }

    @staticmethod
    def _organization_names(text: str, claim_ids: list[str]) -> set[str]:
        for claim_id in claim_ids:
            text = text.replace(claim_id, "")
        return {match.group(1) for match in ORG_NAME_RE.finditer(text)}

    @staticmethod
    def _causal_consequence(text: str) -> str:
        normalized = canonicalize_text(text)
        for cue in ("如果", "一旦", "若"):
            if cue not in normalized:
                continue
            conditional = normalized[normalized.find(cue) + len(cue):]
            parts = re.split(r"[，,；;]", conditional, maxsplit=1)
            if len(parts) == 2:
                return parts[1]
        cause_match = re.search(r"(?:可能)?因(?!此)", normalized)
        if cause_match:
            causal = normalized[cause_match.end():]
            parts = re.split(r"[，,；;]", causal, maxsplit=1)
            if len(parts) == 2:
                return parts[1]
        matches = [
            (normalized.rfind(cue), cue)
            for cue in CAUSAL_CUES
            if cue in normalized
        ]
        if not matches:
            return ""
        position, cue = max(matches)
        consequence = normalized[position + len(cue):]
        return re.split(r"[，,。；;（）()]", consequence, maxsplit=1)[0]

    @staticmethod
    def _shares_specific_phrase(left: str, right: str, *, length: int = 4) -> bool:
        left = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", left).lower()
        right = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", right).lower()
        if len(left) < length:
            return bool(left) and left in right
        return any(left[index:index + length] in right for index in range(len(left) - length + 1))

    def _deterministic_current_view_errors(
        self,
        node: dict[str, Any],
        result: dict[str, Any],
        proposed: dict[str, Any],
        claims: list[dict[str, Any]],
        by_id: dict[str, dict[str, Any]],
    ) -> list[str]:
        errors: list[str] = []
        claim_ids = list(by_id)
        scope_restricted = self._single_company_scope_constraint(node, claims)

        for field, index, item_text in self._evidence_bearing_items(proposed):
            label = self._field_label(field, index)
            refs = self._claim_refs(item_text, by_id)
            supporting_claims = [by_id[claim_id] for claim_id in refs] if refs else claims
            supporting_statements = [
                str(claim.get("statement") or "") for claim in supporting_claims
            ]

            if field in ATOMIC_FUTURE_FIELDS and FUTURE_SEMANTIC_RE.search(item_text):
                future_refs = [
                    claim_id
                    for claim_id in refs
                    if by_id[claim_id].get("nature") in FUTURE_CLAIM_NATURES
                    and str(by_id[claim_id].get("statement") or "").strip()
                ]
                if not future_refs:
                    errors.append(
                        f"Current View {label} future statement requires a guidance/forecast "
                        "Claim; data/fact Claim evidence_excerpt cannot support future guidance"
                    )

            item_numbers = self._number_tokens(item_text, claim_ids)
            supported_numbers: set[str] = set()
            for statement in supporting_statements:
                supported_numbers.update(self._number_tokens(statement, []))
            unsupported_numbers = sorted(item_numbers - supported_numbers)
            if unsupported_numbers:
                errors.append(
                    f"Current View {label} contains unsupported numeric fact(s): "
                    + ", ".join(unsupported_numbers)
                )

            organizations = self._organization_names(item_text, claim_ids)
            unsupported_organizations = sorted(
                organization
                for organization in organizations
                if not any(organization in statement for statement in supporting_statements)
                and not any(
                    organization in str(claim.get("attributed_to") or "")
                    for claim in supporting_claims
                )
            )
            if unsupported_organizations:
                errors.append(
                    f"Current View {label} contains unsupported company/supplier(s): "
                    + ", ".join(unsupported_organizations)
                )

            consequence = self._causal_consequence(item_text)
            high_risk_consequence = any(
                cue in consequence for cue in ("价格战", "垄断", "淘汰")
            )
            causal_supported = any(
                self._shares_specific_phrase(consequence, statement)
                for statement in supporting_statements
            )
            if (
                consequence
                and (scope_restricted or high_risk_consequence)
                and not causal_supported
            ):
                errors.append(
                    f"Current View {label} contains unsupported causal inference: "
                    f"{consequence}"
                )
                continue

            asserted_trends = [cue for cue in TREND_CUES if cue in item_text]
            if (
                asserted_trends
                and scope_restricted
                and not any(qualifier in item_text for qualifier in TREND_QUALIFIERS)
                and not any(
                    trend in statement
                    for trend in asserted_trends
                    for statement in supporting_statements
                )
            ):
                errors.append(
                    f"Current View {label} contains unsupported established trend: "
                    + ", ".join(asserted_trends)
                )

        gap_cues = (
            "缺少", "缺乏", "缺失", "不足", "待验证", "尚待", "需要跟踪", "需跟踪",
            "需要验证", "需验证", "尚不清楚", "未知", "无法确认", "信息不足",
        )
        watch_cues = ("跟踪", "关注", "监测", "观察", "待验证", "需要验证", "需验证")
        question_cues = ("是否", "？", "?", "待验证", "需要验证", "需验证", "缺少", "缺乏")
        open_fields = (
            ("knowledge_gaps", proposed.get("knowledge_gaps") or [], gap_cues),
            ("key_watch_items", proposed.get("key_watch_items") or [], watch_cues),
            ("knowledge_gaps", result.get("knowledge_gaps") or [], gap_cues),
            (
                "research_question_candidates",
                result.get("research_question_candidates") or [],
                question_cues,
            ),
        )
        for field, values, cues in open_fields:
            if not isinstance(values, list):
                continue
            for index, item in enumerate(values):
                item_text = self._item_text(item)
                if item_text.strip() and not any(cue in item_text for cue in cues):
                    errors.append(
                        f"Current View {field}[{index}] must be explicitly framed as "
                        "missing evidence, pending validation, or tracking"
                    )
        return errors

    @staticmethod
    def _target_terms(node: dict[str, Any]) -> list[str]:
        terms = [node.get("canonical_name") or "", *(node.get("aliases") or [])]
        return [canonicalize_text(str(term)).lower() for term in terms if canonicalize_text(str(term))]

    @classmethod
    def _contains_target(cls, text: str, node: dict[str, Any]) -> bool:
        normalized = canonicalize_text(text).lower()
        return any(term in normalized for term in cls._target_terms(node))

    @staticmethod
    def _attribution_supported(text: str, claim: dict[str, Any], *, judgment: bool) -> bool:
        normalized = canonicalize_text(text)
        subjects = attribution_subjects(str(claim.get("attributed_to") or ""))
        nature = claim.get("nature") or ""
        generic = {
            "company_guidance": ("公司", "管理层"),
            "expert_judgment": ("专家", "分析师", "研究员"),
            "broker_forecast": ("券商", "机构", "分析师"),
            "market_rumor": ("市场传闻", "传闻", "市场消息"),
            "user_judgment": ("用户",),
            "ai_inference": ("AI推断", "模型推断"),
        }.get(nature, ())
        has_subject = (
            any(subject in normalized for subject in subjects)
            if subjects
            else any(cue in normalized for cue in generic)
        )
        if not judgment:
            return has_subject
        markers = (
            "认为", "判断", "预计", "预判", "指引", "表示", "称", "披露",
            "展望", "看好", "计划", "目标", "拟", "将", "可能", "或", "传闻", "据传", "推断",
        )
        return has_subject and any(marker in normalized for marker in markers)

    def _single_company_scope_constraint(
        self, node: dict[str, Any], evidence: list[dict[str, Any]]
    ) -> bool:
        if node.get("primary_type") not in NON_ENTITY_SCOPE_TYPES:
            return False
        companies = {
            company for item in evidence if (company := self._company_subject(item))
        }
        industry_terms = ("行业", "产业", "市场", "全球")
        industry_level_primary = any(
            item.get("nature") in {"fact", "data"}
            and any(term in canonicalize_text(str(item.get("scope") or "")) for term in industry_terms)
            and not self._company_subject(item)
            and item.get("origin_type") == "primary"
            and item.get("source_rank") in MATERIAL_QUALITY_RANKS
            for item in evidence
            if item.get("claim_id")
        )
        company_sources = {
            self._independence_key(item)
            for item in evidence
            if self._company_subject(item) and self._independence_key(item)
        }
        multi_company_cross_validation = len(companies) >= 2 and len(company_sources) >= 2
        return bool(companies) and not industry_level_primary and not multi_company_cross_validation

    @classmethod
    def _scope_assertion_exceeds_single_company(
        cls, text: str, node: dict[str, Any]
    ) -> bool:
        leading = re.split(
            r"[，,；;]|但|然而|不过|可是", canonicalize_text(text), maxsplit=1
        )[0]
        qualifiers = (
            "公司侧", "单一公司", "公司样本", "样本显示", "验证样本",
            "验证信号", "尚不足", "待验证", "不能确认", "无法确认",
        )
        if any(qualifier in leading for qualifier in qualifiers):
            return False
        deterministic = (
            "已经", "已确认", "确认进入", "确认处于", "处于", "进入",
            "确定", "必然", "全面上行", "长期上行", "整体改善",
        )
        broad_terms = ("行业", "产业", "市场", "全行业", "整体")
        broad_assertion = any(term in leading for term in broad_terms)
        if not broad_assertion:
            broad_assertion = any(
                re.search(re.escape(term) + r".{0,12}(?:处于|进入|已确认|长期上行|整体改善)", leading)
                for term in cls._target_terms(node)
            )
        return broad_assertion and any(cue in leading for cue in deterministic)

    def _validate_cited_items(
        self, field: str, items: list[Any], by_id: dict[str, dict[str, Any]], *,
        key_facts: bool = False,
    ) -> None:
        for index, item in enumerate(items):
            item_text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
            refs = self._claim_refs(item_text, by_id)
            if not refs:
                raise ValueError(f"Current View {field}[{index}] must retain at least one Claim ID")
            for claim_id in refs:
                claim = by_id[claim_id]
                nature = claim.get("nature") or ""
                if key_facts and nature not in KEY_FACT_NATURES:
                    raise ValueError(
                        f"Current View key_facts cannot use judgment Claim {claim_id} ({nature})"
                    )
                judgment_attribution = (
                    isinstance(item, str)
                    and not key_facts
                    and (
                        field == "core_logic"
                        or nature
                        in {
                            "expert_judgment",
                            "broker_forecast",
                            "market_rumor",
                            "user_judgment",
                            "ai_inference",
                        }
                    )
                )
                if nature in JUDGMENT_NATURES and not self._attribution_supported(
                    item_text, claim, judgment=judgment_attribution,
                ):
                    raise ValueError(
                        f"Current View {field}[{index}] must preserve attribution for {claim_id}"
                    )
                company = self._company_subject(claim)
                if company and company not in canonicalize_text(item_text):
                    raise ValueError(
                        f"Current View {field}[{index}] must preserve company subject for {claim_id}"
                    )

    def _major_supplier_errors(
        self,
        items: list[Any],
        by_id: dict[str, dict[str, Any]],
    ) -> list[str]:
        errors: list[str] = []
        for index, item in enumerate(items):
            item_text = self._item_text(item)
            refs = self._claim_refs(item_text, by_id)
            statements = [
                canonicalize_text(str(by_id[claim_id].get("statement") or ""))
                for claim_id in refs
            ]
            if not any(
                cue in statement
                for statement in statements
                for cue in SUPPLIER_IDENTITY_CUES
            ):
                errors.append(
                    "Current View type_specific.major_suppliers"
                    f"[{index}] lacks explicit supplier identity Evidence in cited Claim statement"
                )
                continue
            claimed_strength = [
                cue for cue in SUPPLIER_STRENGTH_CUES if cue in item_text
            ]
            if claimed_strength and not any(
                cue in statement
                for statement in statements
                for cue in claimed_strength
            ):
                errors.append(
                    "Current View type_specific.major_suppliers"
                    f"[{index}] supplier strength exceeds cited Claim statement"
                )
        return errors

    def _supply_capacity_retention_errors(
        self,
        items: list[Any],
        claims: list[dict[str, Any]],
        by_id: dict[str, dict[str, Any]],
    ) -> list[str]:
        grouped: dict[str, dict[str, list[str]]] = {}
        for claim in claims:
            statement = canonicalize_text(str(claim.get("statement") or ""))
            scope = canonicalize_text(str(claim.get("scope") or "")).lower()
            if not scope or not any(cue in statement for cue in SUPPLY_CAPACITY_CUES):
                continue
            nature = claim.get("nature") or ""
            kind = (
                "guidance"
                if nature in FUTURE_CLAIM_NATURES
                else "actual" if nature in {"fact", "data"} else ""
            )
            if kind:
                grouped.setdefault(scope, {"actual": [], "guidance": []})[kind].append(
                    claim["claim_id"]
                )

        item_refs = [
            set(self._claim_refs(self._item_text(item), by_id)) for item in items
        ]
        errors: list[str] = []
        for scope, paired in sorted(grouped.items()):
            if not paired["actual"] or not paired["guidance"]:
                continue
            for claim_id in paired["actual"]:
                if not any(
                    claim_id in refs
                    and not any(
                        by_id[ref].get("nature") in FUTURE_CLAIM_NATURES
                        for ref in refs
                    )
                    for refs in item_refs
                ):
                    errors.append(
                        "Product type_specific.supply_capacity must retain paired Actual "
                        f"Claim {claim_id} for scope {scope} in a separate item"
                    )
            for claim_id in paired["guidance"]:
                if not any(
                    claim_id in refs
                    and not any(
                        by_id[ref].get("nature") in {"fact", "data"}
                        for ref in refs
                    )
                    for refs in item_refs
                ):
                    errors.append(
                        "Product type_specific.supply_capacity must retain paired Guidance "
                        f"Claim {claim_id} for scope {scope} in a separate item"
                    )
        return errors

    def _validate_current_view_quality(
        self, node: dict[str, Any], result: dict[str, Any], evidence: list[dict[str, Any]],
    ) -> None:
        proposed = result.get("proposed_current_view")
        if not isinstance(proposed, dict):
            raise ValueError("Current View proposal must contain proposed_current_view")
        claims = [item for item in evidence if item.get("claim_id")]
        by_id = {item["claim_id"]: item for item in claims}
        evidence_ids = proposed.get("evidence_claim_ids") or []
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError("Current View must retain evidence_claim_ids")
        if any(claim_id not in by_id for claim_id in evidence_ids):
            raise ValueError("Current View evidence_claim_ids contain unknown Evidence")

        one_line_value = proposed.get("one_line_conclusion")
        investment_value = proposed.get("investment_implication")
        if not isinstance(one_line_value, str) or not isinstance(investment_value, str):
            raise ValueError(
                "Current View one_line_conclusion and investment_implication must be strings"
            )
        one_line = one_line_value.strip()
        investment = investment_value.strip()
        if not one_line or not investment:
            raise ValueError("Current View requires one_line_conclusion and investment_implication")
        list_fields = {
            field: proposed.get(field) or []
            for field in ("core_logic", "key_facts", "major_risks", "key_watch_items")
        }
        for field, items in list_fields.items():
            if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
                raise ValueError(f"Current View {field} must be an array of strings")
        for field in ("core_logic", "major_risks", "key_watch_items"):
            if not list_fields[field]:
                raise ValueError(f"Current View {field} cannot be empty")

        target_fields = {
            "one_line_conclusion": one_line,
            "core_logic": " ".join(list_fields["core_logic"]),
            "investment_implication": investment,
            "key_watch_items": " ".join(list_fields["key_watch_items"]),
        }
        for field, text in target_fields.items():
            if not self._contains_target(text, node):
                raise ValueError(f"Current View {field} must be target-Node-centric")
        for index, risk in enumerate(list_fields["major_risks"]):
            if not self._contains_target(risk, node) and not self._claim_refs(risk, by_id):
                raise ValueError(
                    f"Current View major_risks[{index}] must mention the target Node or cite its Evidence"
                )

        self._validate_cited_items("core_logic", list_fields["core_logic"], by_id)
        self._validate_cited_items("key_facts", list_fields["key_facts"], by_id, key_facts=True)
        for risk in list_fields["major_risks"]:
            if self._claim_refs(risk, by_id):
                self._validate_cited_items("major_risks", [risk], by_id)

        if self._single_company_scope_constraint(node, claims):
            scoped_fields = [
                ("one_line_conclusion", one_line),
                ("investment_implication", investment),
                *(("core_logic", item) for item in list_fields["core_logic"]),
                *(("major_risks", item) for item in list_fields["major_risks"]),
            ]
            for field, text in scoped_fields:
                if self._scope_assertion_exceeds_single_company(text, node):
                    raise ValueError(
                        f"Current View {field} exceeds single-company Evidence scope"
                    )

        type_specific = proposed.get("type_specific")
        if not isinstance(type_specific, dict):
            raise ValueError("Current View type_specific must be an object")
        product_errors: list[str] = []
        if node.get("primary_type") == "Product":
            missing = PRODUCT_TYPE_FIELDS - set(type_specific)
            if missing:
                raise ValueError(
                    "Product Current View missing type_specific fields: " + ", ".join(sorted(missing))
                )
            for field in sorted(PRODUCT_TYPE_FIELDS):
                items = type_specific[field]
                if not isinstance(items, list) or any(
                    not isinstance(item, (str, dict)) for item in items
                ):
                    raise ValueError(
                        f"Product type_specific.{field} must be an array of strings or objects"
                    )
                self._validate_cited_items(f"type_specific.{field}", items, by_id)

            for index, item in enumerate(type_specific["applications"]):
                item_text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                refs = self._claim_refs(item_text, by_id)
                for claim_id in refs:
                    claim = by_id[claim_id]
                    evidence_text = canonicalize_text(
                        f"{claim.get('statement') or ''} {claim.get('evidence_excerpt') or ''}"
                    ).lower()
                    if not any(cue in evidence_text for cue in APPLICATION_RELATION_CUES):
                        raise ValueError(
                            f"Product type_specific.applications[{index}] lacks explicit application Evidence"
                        )

            product_errors.extend(
                self._major_supplier_errors(type_specific["major_suppliers"], by_id)
            )
            product_errors.extend(
                self._supply_capacity_retention_errors(
                    type_specific["supply_capacity"], claims, by_id
                )
            )

            watch_text = " ".join(list_fields["key_watch_items"])
            required_watch_cues = {
                "industry supply/demand": ("供需", "供给", "库存", "产能利用率"),
                "competitors": ("竞争", "对手", "同行", "厂商", "供应商"),
                "downstream demand": ("下游", "需求", "应用"),
            }
            for label, cues in required_watch_cues.items():
                if not any(cue in watch_text for cue in cues):
                    raise ValueError(f"Product Current View key_watch_items missing {label}")
            if not any(cue in investment for cue in ("产业", "行业", "供应链", "产品")):
                raise ValueError("Product investment_implication must state product/industry implications")

        deterministic_errors = product_errors + self._deterministic_current_view_errors(
            node, result, proposed, claims, by_id
        )
        if deterministic_errors:
            raise CurrentViewValidationError(deterministic_errors)

    def _apply_initial_evidence_profile(
        self, result: dict[str, Any], evidence: list[dict[str, Any]]
    ) -> None:
        profile = self._evidence_profile(evidence)
        result.update(profile)
        proposed = result.get("proposed_current_view")
        if isinstance(proposed, dict):
            proposed["evidence_profile"] = profile
        if result.get("change_level") == "initial":
            semantic = dict(result.get("evidence_sufficiency") or {})
            model_sufficient = semantic.get("sufficient") is not False
            source_sufficient = profile["evidence_source_count"] >= 1
            sufficient = source_sufficient and model_sufficient
            original_reason = str(semantic.get("reason") or "").strip()
            semantic.update(profile)
            semantic["sufficient"] = sufficient
            if not source_sufficient:
                semantic["reason"] = "Initial View requires at least one Evidence Source"
            elif not model_sufficient:
                semantic["reason"] = (
                    "Initial View semantic Evidence Scope review found insufficient support"
                    + (f": {original_reason}" if original_reason else "")
                )
            else:
                semantic["reason"] = (
                    "Initial View permits a single source; this proposal uses "
                    f"{profile['evidence_source_count']} Source(s) representing "
                    f"{profile['independent_evidence_source_count']} independent underlying Source(s). "
                    "Evidence Scope Constraint applies."
                )
            result["evidence_sufficiency"] = semantic

    def _programmatic_evidence_sufficiency(
        self, level: str, evidence: list[dict[str, Any]], semantic: dict[str, Any]
    ) -> tuple[bool, str]:
        if level == "initial":
            profile = self._evidence_profile(evidence)
            if profile["evidence_source_count"] >= 1:
                return True, "Initial View permits one Source; Evidence Scope Constraint applies"
            return False, "Initial View requires at least one Evidence Source"
        if level not in {"material", "thesis"}:
            return True, "No elevated evidence threshold required"

        claims = [item for item in evidence if item.get("claim_id")]
        by_id = {item["claim_id"]: item for item in claims}
        direct_ids = set(semantic.get("direct_primary_claim_ids") or [])
        decisive_ids = set(semantic.get("decisive_primary_claim_ids") or [])

        def confidence(item: dict[str, Any]) -> float:
            value = item.get("confidence")
            return float(value) if value is not None else 0.0

        direct_primary = [
            by_id[cid] for cid in direct_ids & by_id.keys()
            if by_id[cid].get("origin_type") == "primary"
            and by_id[cid].get("source_rank") in HIGH_PRIMARY_RANKS
            and confidence(by_id[cid]) >= 0.80
        ]
        decisive_primary = [
            by_id[cid] for cid in decisive_ids & by_id.keys()
            if by_id[cid].get("origin_type") == "primary"
            and by_id[cid].get("source_rank") in HIGH_PRIMARY_RANKS
            and confidence(by_id[cid]) >= 0.85
        ]

        if level == "material":
            if direct_primary:
                return True, "One high-confidence direct Primary Evidence"
            quality = [
                item for item in claims
                if item.get("source_rank") in MATERIAL_QUALITY_RANKS and confidence(item) >= 0.70
            ]
            independent = {self._independence_key(item) for item in quality if self._independence_key(item)}
            if len(independent) >= 2:
                return True, "At least two independent higher-quality Evidence sources"
            return False, "Material requires one high-confidence direct Primary Evidence or two independent higher-quality sources"

        explanation_complete = all(
            str(semantic.get(key) or "").strip()
            for key in ("invalidated_core_assumption", "logic_chain_failure", "conclusion_change")
        )
        if not explanation_complete:
            return False, "Thesis Change must identify the failed core assumption, broken logic chain, and changed conclusion"
        if decisive_primary:
            return True, "One decisive high-confidence Primary Evidence with a complete thesis-break explanation"
        quality = [
            item for item in claims
            if item.get("source_rank") in THESIS_QUALITY_RANKS and confidence(item) >= 0.80
        ]
        independent = {self._independence_key(item) for item in quality if self._independence_key(item)}
        if len(independent) >= 2:
            return True, "At least two independent high-quality Evidence sources with a complete thesis-break explanation"
        return False, "Thesis Change requires decisive Primary Evidence or two independent high-quality sources"

    def _create_gap(self, node_id: str, gap: dict[str, Any]) -> str | None:
        title = (gap.get("title") or "").strip()
        if not title:
            return None
        existing = self.db.one(
            "SELECT gap_id FROM knowledge_gaps WHERE node_id=? AND title=? AND status IN ('open','reopened','needs_refresh') LIMIT 1",
            (node_id, title),
        )
        if existing:
            return existing["gap_id"]
        gap_id = make_id("GAP")
        ts = now_iso()
        self.db.execute(
            """INSERT INTO knowledge_gaps(gap_id,node_id,title,description,status,source_claim_ids_json,freshness_due,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (gap_id, node_id, title, gap.get("description", ""), "open",
             json.dumps(gap.get("source_claim_ids") or [], ensure_ascii=False), gap.get("freshness_due", ""), ts, ts),
        )
        return gap_id

    def _create_rq_candidate(self, candidate: dict[str, Any], base_node_id: str, claim_ids: list[str], batch_id: str) -> str | None:
        question = (candidate.get("question") or candidate.get("canonical_name") or "").strip()
        if not question:
            return None
        canonical_name = (candidate.get("canonical_name") or question).strip()
        if self.db.find_node_by_name_or_alias(canonical_name) or self.db.pending_new_node_proposal_exists(canonical_name):
            return None
        related = list(dict.fromkeys([base_node_id, *(candidate.get("related_node_ids") or [])]))
        payload = {
            "canonical_name": canonical_name,
            "primary_type": "ResearchQuestion",
            "aliases": [],
            "description": candidate.get("reason", ""),
            "suggested_parent_node_ids": [],
            "candidate_kind": "research_question",
            "question": question,
            "importance": candidate.get("importance", ""),
            "what_would_change_my_mind": candidate.get("what_would_change_my_mind", ""),
            "related_node_ids": related,
            "related_claim_ids": claim_ids,
        }
        pid = self.db.add_proposal(
            "new_node", payload, reason="Knowledge Gap upgraded to Research Question candidate",
            propagation_batch_id=batch_id,
        )
        write_proposal(self.cfg, self.db.proposal(pid))
        return pid

    def _create_current_view_proposal(
        self, node_id: str, result: dict[str, Any], claim_ids: list[str], trigger_source_id: str,
        batch_id: str, context: dict[str, Any], impact_id: str,
    ) -> str:
        current = self.db.current_view(node_id)
        payload = {
            "node_id": node_id,
            "change_level": result.get("change_level", "minor"),
            "reason": result.get("reason", ""),
            "scope_normalization_notes": result.get("scope_normalization_notes") or [],
            "evidence_sufficiency": result.get("evidence_sufficiency") or {},
            "programmatic_evidence_sufficiency": result.get("programmatic_evidence_sufficiency") or {},
            "evidence_source_count": result.get("evidence_source_count", 0),
            "independent_evidence_source_count": result.get("independent_evidence_source_count", 0),
            "source_rank_distribution": result.get("source_rank_distribution") or {},
            "source_origin_distribution": result.get("source_origin_distribution") or {},
            "evidence_scope": result.get("evidence_scope") or "industry_level",
            "proposed_current_view": result.get("proposed_current_view") or {},
            "evidence_claim_ids": claim_ids,
            "trigger_source_id": trigger_source_id,
            "previous_view_id": current["view_id"] if current else "",
            "previous_version": current["version"] if current else "",
            "context": context,
        }
        pid = self.db.add_proposal(
            "current_view_change", payload, target_node_id=node_id, reason=result.get("reason", ""),
            propagation_batch_id=batch_id, source_impact_id=impact_id,
        )
        write_proposal(self.cfg, self.db.proposal(pid))
        return pid

    @staticmethod
    def _queue_order(path_type: str) -> int:
        return 10 if path_type == "structural" else 20 if path_type == "related" else 0

    def _target_view_version(self, conn: sqlite3.Connection, node_id: str) -> str:
        row = conn.execute(
            f"""SELECT version FROM current_views WHERE node_id=? AND status='official'
                ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1""",
            (node_id,),
        ).fetchone()
        return row["version"] if row else NO_TARGET_VIEW

    def _insert_impact_conn(
        self, conn: sqlite3.Connection, batch_id: str, trigger_type: str, trigger_id: str, node_id: str,
        path_type: str, status: str, context: dict[str, Any],
    ) -> str | None:
        impact_id = make_id("IMP")
        target_version = self._target_view_version(conn, node_id)
        payload = json.dumps(context, ensure_ascii=False)
        try:
            conn.execute(
                """INSERT INTO impact_reviews(
                   impact_id,batch_id,trigger_type,trigger_id,node_id,path_type,status,reason,target_view_version,
                   payload_json,queue_order,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (impact_id, batch_id, trigger_type, trigger_id, node_id, path_type, status, payload, target_version,
                 payload, self._queue_order(path_type), now_iso()),
            )
            return impact_id
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint" in str(exc):
                return None
            raise

    def _insert_impact(
        self, batch_id: str, trigger_type: str, trigger_id: str, node_id: str, path_type: str,
        status: str, context: dict[str, Any],
    ) -> str | None:
        with self.db.transaction(immediate=True) as conn:
            return self._insert_impact_conn(
                conn, batch_id, trigger_type, trigger_id, node_id, path_type, status, context,
            )

    def evaluate_node(
        self, *, batch_id: str, trigger_type: str, trigger_id: str, node_id: str, path_type: str,
        claim_ids: list[str], trigger_source_id: str = "", context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = {**(context or {}), "claim_ids": claim_ids, "trigger_source_id": trigger_source_id}
        impact_id = self._insert_impact(
            batch_id, trigger_type, trigger_id, node_id, path_type, "pending", context,
        )
        if impact_id is None:
            return {"status": "already_reviewed", "proposal_id": "", "gaps": [], "rq_proposals": []}
        try:
            return self._evaluate_impact_row(impact_id)
        except Exception as exc:
            self._mark_failed(impact_id, exc)
            return {
                "status": "failed", "terminal": True, "proposal_id": "",
                "gaps": [], "rq_proposals": [], "error": str(exc),
            }

    def _mark_failed(self, impact_id: str, exc: Exception) -> None:
        self.db.execute(
            "UPDATE impact_reviews SET status='failed',last_error=?,evaluated_at=? WHERE impact_id=?",
            (str(exc), now_iso(), impact_id),
        )

    def _evaluate_impact_row(self, impact_id: str) -> dict[str, Any]:
        from .impact_recovery import ImpactRecoveryService

        return ImpactRecoveryService(
            self.cfg, self.db, self.analyzer
        ).retry(impact_id, max_repairs=2)

    def enqueue_from_accepted_view(
        self, conn: sqlite3.Connection, view: dict[str, Any], proposal_payload: dict[str, Any], batch_id: str,
    ) -> None:
        node_id = view["node_id"]
        claim_ids = proposal_payload.get("evidence_claim_ids") or []
        trigger_source_id = proposal_payload.get("trigger_source_id", "")
        propagated_change = {
            "node_id": node_id,
            "old_version": proposal_payload.get("previous_version", ""),
            "new_version": view["version"],
            "change_level": proposal_payload.get("change_level", ""),
            "reason": proposal_payload.get("reason", ""),
            "recent_change": (proposal_payload.get("proposed_current_view") or {}).get("recent_change", ""),
        }
        relations = conn.execute(
            "SELECT * FROM node_relations WHERE status='current' AND (from_node_id=? OR to_node_id=?)",
            (node_id, node_id),
        ).fetchall()
        for row in relations:
            relation = dict(row)
            other = relation["to_node_id"] if relation["from_node_id"] == node_id else relation["from_node_id"]
            relation["other_node_id"] = other
            relation["direction"] = "out" if relation["from_node_id"] == node_id else "in"
            path_type = "structural" if relation["relation_type"] == "part_of" else "related"
            context = {
                "trigger_node_id": node_id,
                "relation": relation,
                "propagated_change": propagated_change,
                "claim_ids": claim_ids,
                "trigger_source_id": trigger_source_id,
            }
            self._insert_impact_conn(
                conn, batch_id, "current_view", view["view_id"], other, path_type, "pending", context,
            )

    def start_from_accepted_view(
        self, view: dict[str, Any], proposal_payload: dict[str, Any], batch_id: str = "", *,
        conn: sqlite3.Connection | None = None, run: bool = True,
    ) -> str:
        batch_id = batch_id or make_id("BATCH")
        if conn is not None:
            self.enqueue_from_accepted_view(conn, view, proposal_payload, batch_id)
            return batch_id
        with self.db.transaction(immediate=True) as tx:
            self.enqueue_from_accepted_view(tx, view, proposal_payload, batch_id)
        if run:
            self.run_batch(batch_id)
        return batch_id

    def run_batch(self, batch_id: str) -> None:
        if not batch_id:
            return
        while True:
            pending_proposal = self.db.one(
                "SELECT proposal_id FROM proposals WHERE propagation_batch_id=? AND status='pending' LIMIT 1",
                (batch_id,),
            )
            if pending_proposal:
                return
            row = self.db.one(
                """SELECT impact_id FROM impact_reviews
                   WHERE batch_id=? AND status IN ('pending','deferred','retry','needs_llm')
                   ORDER BY queue_order,created_at,impact_id LIMIT 1""",
                (batch_id,),
            )
            if not row:
                return
            self.db.execute("UPDATE impact_reviews SET status='pending' WHERE impact_id=?", (row["impact_id"],))
            try:
                result = self._evaluate_impact_row(row["impact_id"])
            except Exception as exc:
                self._mark_failed(row["impact_id"], exc)
                continue
            if result.get("status") in {"proposed", "needs_llm", "retry"}:
                return

    def resume_batch(self, batch_id: str) -> None:
        self.run_batch(batch_id)
