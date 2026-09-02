"""Pure provenance-based Source-quality classification for Phase 3C.

This module classifies explicit metadata only.  It does not inspect Source text,
run semantic guards, or participate in extraction or Production admission.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CLEAN_TEXT_SOURCE = "CLEAN_TEXT_SOURCE"
TRANSCRIPT_TEXT_SOURCE = "TRANSCRIPT_TEXT_SOURCE"
AUDIO_DERIVED_TRANSCRIPT = "AUDIO_DERIVED_TRANSCRIPT"
UNKNOWN_TEXT_QUALITY = "UNKNOWN_TEXT_QUALITY"

TEXT = "TEXT"
AUDIO = "AUDIO"
UNKNOWN = "UNKNOWN"

_CLEAN_SOURCE_ORIGINS = {
    "AUTHORED_TEXT",
    "OFFICIAL_PUBLICATION",
    "FORMAL_WRITTEN_MATERIAL",
}
_CLEAN_DOCUMENT_TYPES = {
    "COMPANY_ANNOUNCEMENT",
    "FORMAL_FILING",
    "FORMAL_REPORT",
    "OFFICIAL_PRESENTATION",
    "PUBLISHED_TECHNICAL_PAPER",
}
_TRANSCRIPT_SOURCE_ORIGINS = {
    "SPEECH_TRANSCRIPT",
    "TRANSCRIPT_TEXT",
}
_TRANSCRIPT_DOCUMENT_TYPES = {
    "CONFERENCE_CALL_TRANSCRIPT",
    "EXPERT_CALL_TRANSCRIPT",
    "INTERVIEW_TRANSCRIPT",
    "MEETING_TRANSCRIPT",
    "TRANSCRIPT",
}
_AUDIO_SOURCE_ORIGINS = {
    "AUDIO_DERIVED_TRANSCRIPT",
    "AUDIO_TRANSCRIPT",
    "ASR_TRANSCRIPT",
}


def _token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")


def _explicit_bool(value: Any) -> tuple[bool | None, bool]:
    if value is None:
        return None, True
    if isinstance(value, bool):
        return value, True
    return None, False


def classify_source_quality(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a Source from explicit provenance metadata.

    Recognized provenance fields are ``source_origin``, ``document_type``,
    ``authoritative_medium``, ``transcript_derived``, and ``audio_derived``.
    File extensions, filenames, titles, and linguistic quality are deliberately
    ignored.  Missing, malformed, or conflicting provenance fails to
    ``UNKNOWN_TEXT_QUALITY``.
    """
    source_origin = _token(metadata.get("source_origin"))
    document_type = _token(metadata.get("document_type"))
    medium_token = _token(metadata.get("authoritative_medium"))
    transcript_derived, transcript_valid = _explicit_bool(
        metadata.get("transcript_derived")
    )
    audio_derived, audio_valid = _explicit_bool(metadata.get("audio_derived"))

    medium_valid = not medium_token or medium_token in {TEXT, AUDIO, UNKNOWN}
    authoritative_medium = medium_token if medium_token in {TEXT, AUDIO} else UNKNOWN

    clean_marker = (
        source_origin in _CLEAN_SOURCE_ORIGINS
        or document_type in _CLEAN_DOCUMENT_TYPES
    )
    transcript_marker = (
        source_origin in _TRANSCRIPT_SOURCE_ORIGINS
        or document_type in _TRANSCRIPT_DOCUMENT_TYPES
    )
    audio_marker = source_origin in _AUDIO_SOURCE_ORIGINS or audio_derived is True

    invalid_or_conflicting = (
        not transcript_valid
        or not audio_valid
        or not medium_valid
        or (clean_marker and (transcript_marker or audio_marker))
        or (transcript_derived is False and (transcript_marker or audio_marker))
        or (audio_derived is False and source_origin in _AUDIO_SOURCE_ORIGINS)
        or (audio_marker and authoritative_medium == TEXT)
        or (clean_marker and authoritative_medium == AUDIO)
    )

    if invalid_or_conflicting:
        source_quality_class = UNKNOWN_TEXT_QUALITY
        classification_basis = "conflicting_or_invalid_explicit_provenance"
    elif audio_marker or (
        transcript_derived is True and authoritative_medium == AUDIO
    ):
        source_quality_class = AUDIO_DERIVED_TRANSCRIPT
        authoritative_medium = AUDIO
        transcript_derived = True
        classification_basis = "explicit_audio_derived_provenance"
    elif transcript_marker or transcript_derived is True:
        source_quality_class = TRANSCRIPT_TEXT_SOURCE
        authoritative_medium = TEXT
        transcript_derived = True
        classification_basis = "explicit_transcript_provenance"
    elif (
        clean_marker
        and authoritative_medium == TEXT
        and transcript_derived is False
        and audio_derived in {False, None}
    ):
        source_quality_class = CLEAN_TEXT_SOURCE
        classification_basis = "explicit_authored_text_provenance"
    else:
        source_quality_class = UNKNOWN_TEXT_QUALITY
        classification_basis = "insufficient_explicit_provenance"

    auto_admission_eligible = source_quality_class == CLEAN_TEXT_SOURCE
    return {
        "source_quality_class": source_quality_class,
        "authoritative_medium": authoritative_medium,
        "transcript_derived": transcript_derived,
        "auto_admission_eligible": auto_admission_eligible,
        "human_review_required": not auto_admission_eligible,
        "classification_basis": classification_basis,
        "semantic_admission_guard_activated": False,
    }
