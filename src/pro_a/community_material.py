"""Fail-closed ZSXQ bundle intake and deterministic clean-PDF normalization."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import zipfile

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from pro_a.company_material_intent import CompanyMaterialError, company
from .workbench.domains import Domains
from .workbench.review_store import schema_version
from .workbench.source_operations import SourceOperationError


CONTRACT_VERSION = "zsxq-pro-a-community-export-v1"
PROVENANCE_VERSION = "community-source-provenance-v1"
MAX_BUNDLE_BYTES = 20 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 40 * 1024 * 1024
MAX_TOPICS = 100
MAX_EVIDENCE_CHARS = 12000
MAX_TOTAL_EVIDENCE_CHARS = 500000
MAX_COMPRESSION_RATIO = 100
MEMBERS = ("manifest.json", "topics.jsonl")
MANIFEST_FIELDS = frozenset((
    "contract_version", "bundle_id", "bundle_sha256", "company_input", "group_id",
    "group_label", "days", "analysis_source", "generated_at", "input_topic_count",
    "in_range_count", "topic_count", "reportable_topic_count", "omitted_unrelated",
    "omitted_missing_analysis", "topic_ids", "topics_file_sha256", "selection_rule",
    "source_pipeline",
))
TOPIC_FIELDS = frozenset(("topic_id", "published_at", "author", "keyword_sources",
                         "evidence_text", "evidence_text_sha256", "routing"))
ROUTING_FIELDS = frozenset(("reportable", "relevance_level", "category", "credibility"))
SELECTION_RULE = "in_range=true AND reportable=true AND relevance_level!=无实质关联"
SOURCE_PIPELINE = "zsxq-cli read-only topic search/recent scan/detail; DeepSeek routing only"
_SENSITIVE = re.compile(r"(?i)(?:bearer\s+\S+|\b(?:token|cookie|secret|authorization|password|api[_-]?key)\s*[:=]\s*\S+|https?://\S*[?&](?:token|cookie|secret|password|api[_-]?key)=)")
_LOCAL_PATH = re.compile(r"(?i)(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users)/|\.runtime-home)")
_FONT_CANDIDATES = (
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "NotoSansSC-VF.ttf",
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simhei.ttf",
    Path("/usr/share/fonts/truetype/arphic/ukai.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
)


def _fail(code: str = "COMMUNITY_BUNDLE_INVALID", status: int = 422) -> None:
    raise SourceOperationError(code, status)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _decode_json(value: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeError, ValueError, TypeError):
        _fail()
    if not isinstance(decoded, dict) or value != _json_bytes(decoded) + b"\n":
        _fail()
    return decoded


def _date(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail()
    if parsed.tzinfo is None:
        _fail()
    return parsed.astimezone(timezone.utc)


def _sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    date = _date(row["published_at"])
    return (0, -date.timestamp(), row["topic_id"]) if date else (1, 0, row["topic_id"])


def _safe_strings(value: Any) -> None:
    if isinstance(value, str):
        if "\x00" in value or _SENSITIVE.search(value) or _LOCAL_PATH.search(value):
            _fail("COMMUNITY_BUNDLE_SENSITIVE_CONTENT")
    elif isinstance(value, list):
        for item in value:
            _safe_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _safe_strings(key)
            _safe_strings(item)


def parse_bundle(data: bytes) -> dict[str, Any]:
    if not data or len(data) > MAX_BUNDLE_BYTES:
        _fail("COMMUNITY_BUNDLE_TOO_LARGE", 413)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        with archive:
            infos = archive.infolist()
            if [item.filename for item in infos] != list(MEMBERS):
                _fail()
            if sum(item.file_size for item in infos) > MAX_UNCOMPRESSED_BYTES:
                _fail("COMMUNITY_BUNDLE_TOO_LARGE", 413)
            contents = {}
            for info in infos:
                mode = stat.S_IFMT(info.external_attr >> 16)
                if (info.is_dir() or mode == stat.S_IFLNK or info.flag_bits & 1 or
                        info.compress_type != zipfile.ZIP_DEFLATED or
                        info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO):
                    _fail()
                contents[info.filename] = archive.read(info)
                if len(contents[info.filename]) != info.file_size:
                    _fail()
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, ValueError):
        _fail()
    manifest_bytes = contents["manifest.json"]
    topics_bytes = contents["topics.jsonl"]
    manifest = _decode_json(manifest_bytes)
    if set(manifest) != MANIFEST_FIELDS or manifest["contract_version"] != CONTRACT_VERSION:
        _fail("COMMUNITY_BUNDLE_CONTRACT_MISMATCH")
    if (manifest["selection_rule"] != SELECTION_RULE or manifest["source_pipeline"] != SOURCE_PIPELINE or
            manifest["analysis_source"] not in ("detail_search", "detail", "search")):
        _fail()
    if (not isinstance(manifest["topic_count"], int) or isinstance(manifest["topic_count"], bool) or
            manifest["topic_count"] < 0 or manifest["topic_count"] > MAX_TOPICS):
        _fail()
    if manifest["topic_count"] == 0:
        _fail("COMMUNITY_BUNDLE_NO_REPORTABLE_TOPICS")
    if (manifest["reportable_topic_count"] != manifest["topic_count"] or
            not isinstance(manifest["days"], int) or manifest["days"] <= 0):
        _fail()
    for field in ("input_topic_count", "in_range_count", "omitted_unrelated", "omitted_missing_analysis"):
        if not isinstance(manifest[field], int) or manifest[field] < 0:
            _fail()
    if manifest["in_range_count"] != (manifest["topic_count"] + manifest["omitted_unrelated"] +
                                     manifest["omitted_missing_analysis"]):
        _fail()
    if not isinstance(manifest["generated_at"], str):
        _fail()
    _date(manifest["generated_at"])
    if not all(isinstance(manifest[key], str) and manifest[key] for key in
               ("bundle_id", "bundle_sha256", "group_id", "group_label", "company_input")):
        _fail()
    if _sha(topics_bytes) != manifest["topics_file_sha256"]:
        _fail("COMMUNITY_TOPICS_SHA_MISMATCH")
    if manifest["bundle_id"] != "COMMUNITY_BUNDLE_" + manifest["topics_file_sha256"][:24].upper():
        _fail()
    core = {key: value for key, value in manifest.items() if key != "bundle_sha256"}
    if _sha(_json_bytes(core) + b"\n" + topics_bytes) != manifest["bundle_sha256"]:
        _fail("COMMUNITY_BUNDLE_SHA_MISMATCH")
    if not topics_bytes.endswith(b"\n"):
        _fail()
    rows = [_decode_json(line + b"\n") for line in topics_bytes.splitlines()]
    if len(rows) != manifest["topic_count"]:
        _fail()
    if not isinstance(manifest["topic_ids"], list):
        _fail()
    seen = set()
    for row in rows:
        if set(row) != TOPIC_FIELDS or set(row["routing"]) != ROUTING_FIELDS:
            _fail()
        topic_id = row["topic_id"]
        if (not isinstance(topic_id, str) or not topic_id or topic_id != topic_id.strip() or
                topic_id in seen):
            _fail()
        seen.add(topic_id)
        if (not isinstance(row["evidence_text"], str) or not row["evidence_text"] or
                len(row["evidence_text"]) > MAX_EVIDENCE_CHARS or
                _sha(row["evidence_text"].encode("utf-8")) != row["evidence_text_sha256"]):
            _fail("COMMUNITY_EVIDENCE_SHA_MISMATCH")
        if (row["routing"]["reportable"] is not True or
                row["routing"]["relevance_level"] == "无实质关联" or
                not all(isinstance(row["routing"][key], str) for key in
                        ("relevance_level", "category", "credibility")) or
                not isinstance(row["author"], str) or
                not isinstance(row["keyword_sources"], list) or
                not all(isinstance(item, str) for item in row["keyword_sources"])):
            _fail()
        _date(row["published_at"])
    if (sum(len(row["evidence_text"]) for row in rows) > MAX_TOTAL_EVIDENCE_CHARS or
            [row["topic_id"] for row in rows] != manifest["topic_ids"] or
            rows != sorted(rows, key=_sort_key)):
        _fail()
    _safe_strings(manifest)
    _safe_strings(rows)
    return {"manifest": manifest, "topics": rows, "zip_sha256": _sha(data)}


def _wrapped(text: str, width: float, size: float) -> list[str]:
    lines = []
    current = ""
    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
        elif pdfmetrics.stringWidth(current + char, "CommunityChinese", size) > width and current:
            lines.append(current)
            current = char
        else:
            current += char
    lines.append(current)
    return lines


def render_pdf(bundle: dict[str, Any]) -> tuple[bytes, list[dict[str, Any]]]:
    font_path = next((path for path in _FONT_CANDIDATES if path.is_file()), None)
    if font_path is None:
        _fail("COMMUNITY_CHINESE_FONT_UNAVAILABLE", 503)
    pdfmetrics.registerFont(TTFont("CommunityChinese", str(font_path)))
    output = io.BytesIO()
    drawing = canvas.Canvas(output, pagesize=A4, invariant=1, pageCompression=0)
    drawing.setTitle("Community Snapshot")
    drawing.setAuthor("pro_a")
    page_width, page_height = A4
    left, top, bottom = 46, page_height - 48, 48
    page_number = 1
    ranges = []

    def line(value: str, y: float, size: int = 10) -> float:
        nonlocal page_number
        drawing.setFont("CommunityChinese", size)
        for segment in _wrapped(value, page_width - 2 * left, size):
            if y < bottom:
                drawing.showPage()
                page_number += 1
                y = top
                drawing.setFont("CommunityChinese", size)
            drawing.drawString(left, y, segment)
            y -= 15
        return y

    for index, row in enumerate(bundle["topics"]):
        if index:
            drawing.showPage()
            page_number += 1
        start = page_number
        y = top
        y = line("Community Snapshot", y, 15) - 12
        for label, value in (("Topic ID", row["topic_id"]),
                             ("Published At", row["published_at"] or "Unknown"),
                             ("Author", row["author"]),
                             ("Group", bundle["manifest"]["group_label"]),
                             ("Keyword Sources", ", ".join(row["keyword_sources"]))):
            y = line(f"{label}: {value}", y)
        y -= 12
        y = line("Raw sanitized evidence text", y, 11) - 5
        line(row["evidence_text"], y)
        ranges.append({"topic_id": row["topic_id"], "start_page": start, "end_page": page_number})
    drawing.save()
    pdf = output.getvalue()
    reader = PdfReader(io.BytesIO(pdf), strict=True)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not all(row["evidence_text"].replace("\n", "") in extracted.replace("\n", "")
               for row in bundle["topics"]):
        _fail("COMMUNITY_PDF_TEXT_LOSS")
    return pdf, ranges


def provenance(bundle: dict[str, Any], pdf: bytes, ranges: list[dict[str, Any]]) -> dict[str, Any]:
    manifest, rows = bundle["manifest"], bundle["topics"]
    dates = [row["published_at"] for row in rows if row["published_at"]]
    return {
        "contract_version": PROVENANCE_VERSION,
        "bundle_id": manifest["bundle_id"], "bundle_sha256": manifest["bundle_sha256"],
        "provider": "zsxq", "group_id": manifest["group_id"],
        "group_label": manifest["group_label"], "company_input": manifest["company_input"],
        "topic_count": len(rows), "topic_ids": manifest["topic_ids"],
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "topic_page_ranges": ranges,
        "routing_metadata": [{"topic_id": row["topic_id"], **row["routing"]} for row in rows],
        "pdf_sha256": _sha(pdf),
    }


def preview(config: Any, data: bytes, company_id: str) -> dict[str, Any]:
    bundle = parse_bundle(data)
    try:
        target = company(config, company_id)
    except CompanyMaterialError as error:
        raise SourceOperationError(str(error), error.status) from None
    rows, manifest = bundle["topics"], bundle["manifest"]
    dates = [row["published_at"] for row in rows if row["published_at"]]
    return {"target_company": target, "company_input": manifest["company_input"],
            "group_id": manifest["group_id"], "group_label": manifest["group_label"],
            "topic_count": len(rows), "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "bundle_id": manifest["bundle_id"], "bundle_sha256": manifest["bundle_sha256"],
            "trust_policy": "LOW_TRUST_CLUE_ONLY"}


def available_domains(service: Any) -> list[dict[str, str]]:
    with service.store.connect() as connection:
        if schema_version(connection) != "11":
            _fail("COMMUNITY_SCHEMA11_REQUIRED", 409)
        return [dict(row) for row in connection.execute(
            "SELECT domain_id,version,sha256 FROM domain_pack_registry ORDER BY domain_id,version"
        )]


async def import_bundle(service: Any, data: bytes, company_id: str,
                        primary_domain: str, actor: str) -> dict[str, Any]:
    summary = preview(service.config, data, company_id)
    identities = [item for item in available_domains(service) if item["domain_id"] == primary_domain]
    if len(identities) != 1:
        _fail("COMMUNITY_PROCESSING_DOMAIN_INVALID")
    bundle = parse_bundle(data)
    pdf, ranges = render_pdf(bundle)

    async def stream():
        yield pdf

    source = await service.upload(stream(), filename="community_snapshot.pdf",
                                  mime_type="application/pdf")
    with service.store.connect() as connection:
        prior_domain = Domains(service.config).assignment(connection, "Source", source["source_id"])
    if prior_domain and (prior_domain["primary_domain"] != primary_domain or
                         json.loads(prior_domain["packs_json"]) != identities):
        _fail("COMMUNITY_PROCESSING_DOMAIN_CONFLICT", 409)
    Domains(service.config).assign(
        "Source", source["source_id"], primary_domain=primary_domain, packs=identities,
        actor=actor, reason="Operator selected Community processing domain",
        expected_revision=prior_domain["revision"] if prior_domain else 0,
    )
    sidecar = provenance(bundle, pdf, ranges)
    sidecar["target_company_node_id"] = company_id
    sidecar["source_id"] = source["source_id"]
    root = Path(service.config.artifact_root) / "community-provenance"
    root.mkdir(parents=True, exist_ok=True)
    path = root / (bundle["manifest"]["bundle_sha256"] + "-" +
                   _sha(company_id.encode("utf-8"))[:16] + ".json")
    content = _json_bytes(sidecar) + b"\n"
    if path.exists():
        if path.read_bytes() != content:
            _fail("COMMUNITY_PROVENANCE_CONFLICT", 409)
    else:
        try:
            with path.open("xb") as output:
                output.write(content)
        except FileExistsError:
            if path.read_bytes() != content:
                _fail("COMMUNITY_PROVENANCE_CONFLICT", 409)
    event = {"provider": "zsxq", "contract_version": CONTRACT_VERSION,
             "bundle_id": summary["bundle_id"], "bundle_sha256": summary["bundle_sha256"],
             "topic_count": summary["topic_count"], "topic_ids": bundle["manifest"]["topic_ids"],
             "group_id": summary["group_id"], "group_label": summary["group_label"],
             "date_min": summary["date_min"], "date_max": summary["date_max"],
             "provenance_sha256": _sha(content), "pdf_sha256": _sha(pdf),
             "trust_policy": "LOW_TRUST_CLUE_ONLY"}
    key = "community-" + _sha((summary["bundle_sha256"] + ":" + company_id).encode("utf-8"))
    started = service.start(
        source["source_id"], idempotency_key=key,
        company_material_intent={"target_company_node_id": company_id,
                                 "material_kind": "community_material",
                                 "source_channel": "knowledge_community",
                                 "material_date": None, "operator_title": None},
        community_event=event,
    )
    return {"preview": summary, "source": source, **started}
