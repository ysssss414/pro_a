from __future__ import annotations

from pro_a.source_quality import (
    AUDIO,
    AUDIO_DERIVED_TRANSCRIPT,
    CLEAN_TEXT_SOURCE,
    TEXT,
    TRANSCRIPT_TEXT_SOURCE,
    UNKNOWN,
    UNKNOWN_TEXT_QUALITY,
    classify_source_quality,
)


def test_clean_authored_document_is_eligible_subject_to_separate_gates():
    result = classify_source_quality(
        {
            "source_origin": "official_publication",
            "document_type": "formal_report",
            "authoritative_medium": "text",
            "transcript_derived": False,
        }
    )

    assert result["source_quality_class"] == CLEAN_TEXT_SOURCE
    assert result["authoritative_medium"] == TEXT
    assert result["auto_admission_eligible"] is True
    assert result["human_review_required"] is False


def test_explicit_transcript_requires_human_review():
    result = classify_source_quality(
        {
            "source_origin": "speech_transcript",
            "document_type": "expert_call_transcript",
            "transcript_derived": True,
        }
    )

    assert result["source_quality_class"] == TRANSCRIPT_TEXT_SOURCE
    assert result["authoritative_medium"] == TEXT
    assert result["auto_admission_eligible"] is False
    assert result["human_review_required"] is True


def test_audio_derived_transcript_is_not_auto_admission_eligible():
    result = classify_source_quality(
        {
            "source_origin": "asr_transcript",
            "authoritative_medium": "audio",
            "transcript_derived": True,
            "audio_derived": True,
        }
    )

    assert result["source_quality_class"] == AUDIO_DERIVED_TRANSCRIPT
    assert result["authoritative_medium"] == AUDIO
    assert result["auto_admission_eligible"] is False
    assert result["human_review_required"] is True


def test_unknown_provenance_fails_conservatively():
    result = classify_source_quality({"document_type": "unknown"})

    assert result["source_quality_class"] == UNKNOWN_TEXT_QUALITY
    assert result["authoritative_medium"] == UNKNOWN
    assert result["transcript_derived"] is None
    assert result["auto_admission_eligible"] is False
    assert result["human_review_required"] is True


def test_pdf_format_does_not_make_a_transcript_clean():
    result = classify_source_quality(
        {
            "file_format": "pdf",
            "source_origin": "transcript_text",
            "document_type": "conference_call_transcript",
            "transcript_derived": True,
        }
    )

    assert result["source_quality_class"] == TRANSCRIPT_TEXT_SOURCE
    assert result["auto_admission_eligible"] is False


def test_formal_pdf_report_may_be_clean_when_provenance_is_explicit():
    result = classify_source_quality(
        {
            "file_format": "pdf",
            "source_origin": "authored_text",
            "document_type": "formal_report",
            "authoritative_medium": "text",
            "transcript_derived": False,
        }
    )

    assert result["source_quality_class"] == CLEAN_TEXT_SOURCE
    assert result["auto_admission_eligible"] is True


def test_filename_or_title_alone_cannot_establish_clean_status():
    result = classify_source_quality(
        {
            "filename": "official-looking-report.pdf",
            "title": "Formal Industry Report",
            "file_format": "pdf",
        }
    )

    assert result["source_quality_class"] == UNKNOWN_TEXT_QUALITY
    assert result["auto_admission_eligible"] is False


def test_conflicting_provenance_fails_conservatively():
    result = classify_source_quality(
        {
            "source_origin": "official_publication",
            "document_type": "interview_transcript",
            "authoritative_medium": "text",
            "transcript_derived": True,
        }
    )

    assert result["source_quality_class"] == UNKNOWN_TEXT_QUALITY
    assert result["classification_basis"] == (
        "conflicting_or_invalid_explicit_provenance"
    )


def test_source_classification_never_activates_semantic_admission_guard():
    for metadata in (
        {
            "source_origin": "authored_text",
            "document_type": "formal_report",
            "authoritative_medium": "text",
            "transcript_derived": False,
        },
        {
            "source_origin": "speech_transcript",
            "transcript_derived": True,
        },
        {},
    ):
        assert classify_source_quality(metadata)[
            "semantic_admission_guard_activated"
        ] is False
