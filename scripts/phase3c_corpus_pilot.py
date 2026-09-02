from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.config import load_config
from pro_a.corpus_pilot import (
    PilotError,
    apply_production_reviewed_bundle,
    close_pilot2_human_review,
    close_stage1_2_human_review,
    extract_pilot_source,
    format_stage1_report,
    preview_reviewed_bundle,
    rebind_stage1_evidence_locators,
    run_pilot2_controlled_reextraction,
    run_pilot2_real_extraction,
    run_pilot2_gate_a_quote_fidelity,
    run_stage1_3_evidence_scope_diagnostic,
    run_stage1_4_evidence_contract_v2,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 3C controlled live corpus pilot")
    parser.add_argument("--config", default="config.toml")
    commands = parser.add_subparsers(dest="command", required=True)

    extract = commands.add_parser("extract-stage1")
    extract.add_argument("--input", required=True, type=Path)
    extract.add_argument("--output-dir", type=Path)
    extract.add_argument("--production-db", type=Path)

    rebind = commands.add_parser("rebind-stage1_1")
    rebind.add_argument("--bundle", required=True, type=Path)
    rebind.add_argument("--source-file", required=True, type=Path)
    rebind.add_argument("--output-dir", type=Path)
    rebind.add_argument("--production-db", type=Path)

    close_review = commands.add_parser("close-stage1_2-review")
    close_review.add_argument("--bundle", required=True, type=Path)
    close_review.add_argument("--draft-review", required=True, type=Path)
    close_review.add_argument("--decisions", required=True, type=Path)
    close_review.add_argument("--output-dir", type=Path)
    close_review.add_argument("--production-db", type=Path)

    diagnose = commands.add_parser("diagnose-stage1_3")
    diagnose.add_argument("--bundle", required=True, type=Path)
    diagnose.add_argument("--stage1_2-review", required=True, type=Path)
    diagnose.add_argument("--source-file", required=True, type=Path)
    diagnose.add_argument("--decisions", required=True, type=Path)
    diagnose.add_argument("--output-dir", type=Path)
    diagnose.add_argument("--production-db", type=Path)

    replay_v2 = commands.add_parser("replay-stage1_4-v2")
    replay_v2.add_argument("--bundle", required=True, type=Path)
    replay_v2.add_argument("--stage1_2-review", required=True, type=Path)
    replay_v2.add_argument("--stage1_3-diagnostic", required=True, type=Path)
    replay_v2.add_argument("--source-file", required=True, type=Path)
    replay_v2.add_argument("--output-dir", type=Path)
    replay_v2.add_argument("--production-db", type=Path)

    pilot2 = commands.add_parser("run-pilot2-real-extraction")
    pilot2.add_argument("--source-file", required=True, type=Path)
    pilot2.add_argument("--source-search-root", required=True, type=Path)
    pilot2.add_argument("--pilot1-bundle", required=True, type=Path)
    pilot2.add_argument("--pilot1-source", required=True, type=Path)
    pilot2.add_argument("--production-db", type=Path)

    reextract = commands.add_parser("run-pilot2-controlled-reextraction")
    reextract.add_argument("--source-file", required=True, type=Path)
    reextract.add_argument("--source-search-root", required=True, type=Path)
    reextract.add_argument("--historical-run-dir", required=True, type=Path)
    reextract.add_argument("--production-db", type=Path)

    gate_a = commands.add_parser("audit-pilot2-gate-a")
    gate_a.add_argument("--original-bundle", required=True, type=Path)
    gate_a.add_argument("--rebound-bundle", required=True, type=Path)
    gate_a.add_argument("--evidence-draft", required=True, type=Path)
    gate_a.add_argument("--source-file", required=True, type=Path)
    gate_a.add_argument("--original-review", type=Path)
    gate_a.add_argument("--output-dir", type=Path)
    gate_a.add_argument("--production-db", type=Path)

    pilot2_review = commands.add_parser("close-pilot2-human-review")
    pilot2_review.add_argument("--original-bundle", required=True, type=Path)
    pilot2_review.add_argument("--evidence-draft", required=True, type=Path)
    pilot2_review.add_argument("--gate-a", required=True, type=Path)
    pilot2_review.add_argument("--decisions", required=True, type=Path)
    pilot2_review.add_argument("--output-dir", type=Path)
    pilot2_review.add_argument("--production-db", type=Path)

    preview = commands.add_parser("preview-reviewed-bundle")
    preview.add_argument("--bundle", required=True, type=Path)
    preview.add_argument("--review", required=True, type=Path)
    preview.add_argument("--db", type=Path)

    apply = commands.add_parser("apply-production-reviewed-bundle")
    apply.add_argument("--bundle", required=True, type=Path)
    apply.add_argument("--review", required=True, type=Path)
    apply.add_argument("--source-file", required=True, type=Path)
    apply.add_argument("--db", required=True, type=Path, help="Explicit isolated Production-copy database")
    apply.add_argument("--archive-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cfg = load_config(args.config)
    try:
        if args.command == "extract-stage1":
            result = extract_pilot_source(
                args.input, cfg, output_dir=args.output_dir, production_db_path=args.production_db,
            )
            print(format_stage1_report(result))
            return 0
        if args.command == "rebind-stage1_1":
            result = rebind_stage1_evidence_locators(
                args.bundle,
                args.source_file,
                output_dir=args.output_dir,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "original_bundle_unchanged": result["original_bundle_unchanged"],
                "rebound_bundle_path": result["rebound_bundle_path"],
                "review_draft_path": result["review_draft_path"],
                "review_markdown_path": result["review_markdown_path"],
                "metrics_path": result["metrics_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "close-stage1_2-review":
            result = close_stage1_2_human_review(
                args.bundle,
                args.draft_review,
                args.decisions,
                output_dir=args.output_dir,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "inputs_unchanged": result["inputs_unchanged"],
                "review_path": result["review_path"],
                "review_markdown_path": result["review_markdown_path"],
                "metrics_path": result["metrics_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "diagnose-stage1_3":
            result = run_stage1_3_evidence_scope_diagnostic(
                args.bundle,
                args.stage1_2_review,
                args.source_file,
                args.decisions,
                output_dir=args.output_dir,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "inputs_unchanged": result["inputs_unchanged"],
                "diagnostic_path": result["diagnostic_path"],
                "report_path": result["report_path"],
                "metrics_path": result["metrics_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "replay-stage1_4-v2":
            result = run_stage1_4_evidence_contract_v2(
                args.bundle,
                args.stage1_2_review,
                args.stage1_3_diagnostic,
                args.source_file,
                output_dir=args.output_dir,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "inputs_unchanged": result["inputs_unchanged"],
                "contract_path": result["contract_path"],
                "report_path": result["report_path"],
                "metrics_path": result["metrics_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "run-pilot2-real-extraction":
            result = run_pilot2_real_extraction(
                args.source_file,
                args.source_search_root,
                args.pilot1_bundle,
                args.pilot1_source,
                cfg,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "prompt_status": result["prompt_status"],
                "metrics": result["evidence"]["metrics"],
                "production_unchanged": result["production_unchanged"],
                "pilot1_history_unchanged": result["pilot1_history_unchanged"],
                "extraction_bundle": result["extraction"]["extraction_bundle_path"],
                "human_review_draft": result["rebound"]["review_draft_path"],
                "evidence_v2_draft": result["evidence"]["draft_path"],
                "review_surface": result["evidence"]["review_surface_path"],
                "metrics_path": result["evidence"]["metrics_path"],
                "comparison_path": result["comparison"]["comparison_path"],
                "comparison_markdown_path": result["comparison"]["comparison_markdown_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "run-pilot2-controlled-reextraction":
            result = run_pilot2_controlled_reextraction(
                args.source_file,
                args.source_search_root,
                args.historical_run_dir,
                cfg,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "historical_artifacts_unchanged": result["historical_artifacts_unchanged"],
                "metrics_path": result["metrics_path"],
                "quote_fidelity": result["quote_path"],
                "quote_fidelity_report": result["quote_report_path"],
                "comparison": result["comparison_path"],
                "comparison_report": result["comparison_report_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "audit-pilot2-gate-a":
            result = run_pilot2_gate_a_quote_fidelity(
                args.original_bundle,
                args.rebound_bundle,
                args.evidence_draft,
                args.source_file,
                output_dir=args.output_dir,
                production_db_path=args.production_db or cfg.db_path,
                original_review_path=args.original_review,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "gate_a": result["gate_a_path"],
                "report": result["report_path"],
                "metrics_path": result["metrics_path"],
                "review_surface": result["review_surface_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "close-pilot2-human-review":
            result = close_pilot2_human_review(
                args.original_bundle,
                args.evidence_draft,
                args.gate_a,
                args.decisions,
                output_dir=args.output_dir,
                production_db_path=args.production_db or cfg.db_path,
            )
            print(json.dumps({
                "status": result["status"],
                "pilot_run_id": result["pilot_run_id"],
                "metrics": result["metrics"],
                "production_unchanged": result["production_unchanged"],
                "inputs_unchanged": result["inputs_unchanged"],
                "decisions_artifact": result["decisions_artifact_path"],
                "ready": result["ready_path"],
                "report": result["report_path"],
                "metrics_path": result["metrics_path"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "preview-reviewed-bundle":
            result = preview_reviewed_bundle(
                args.bundle, args.review, args.db or cfg.db_path,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "apply-production-reviewed-bundle":
            result = apply_production_reviewed_bundle(
                args.bundle,
                args.review,
                args.source_file,
                db_path=args.db,
                cfg=cfg,
                archive_root=args.archive_root,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except PilotError as exc:
        print(str(exc))
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
