"""Private clean-PDF fixture for Stage 7 Source operations."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.store import Store
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.attribution_store import prepare_attribution
from pro_a.workbench.view_store import prepare_current_views
from pro_a.workbench.impact_store import prepare_impact
from pro_a.workbench.research_store import prepare_research
from pro_a.workbench.cloud_jobs import CloudProfile, prepare_cloud_jobs
from pro_a.workbench.source_operations import SourceOperations, SourceProfile, prepare_source_operations
from workbench_fixture import make_fixture


def stage7_fixture(root: Path, *, max_pdf_bytes: int = 20 * 1024 * 1024):
    seed = make_fixture(root / "seed", mode="PRIVATE")
    phase4_root = root / "phase4"
    phase4_root.mkdir(parents=True)
    knowledge = phase4_root / "pro_a.db"
    shutil.copy2(seed["config"].knowledge_db, knowledge)
    artifacts = root / "private-artifacts"
    config = WorkbenchConfig(
        "PRIVATE", knowledge, root / "state" / "workbench.sqlite3", artifacts,
        "http://127.0.0.1:8000",
    )
    Store(config).initialize()
    prepare_reviews(config)
    prepare_attribution(config)
    prepare_current_views(config)
    prepare_impact(config)
    prepare_research(config)
    stage5 = config.state_db.read_bytes()
    prepare_cloud_jobs(config)
    stage6 = config.state_db.read_bytes()
    prepared = prepare_source_operations(config)
    phase4_config = root / "phase4.toml"
    phase4_config.write_text(
        "[workspace]\nroot = " + json.dumps(str(phase4_root).replace("\\", "/")) + "\n"
        "settle_seconds = 0\n\n"
        "[llm]\nenabled = false\nmodel = \"fake-semantic-v1\"\nmax_retries = 0\n"
        "max_output_tokens = 8192\nmax_chunk_chars = 22000\nmax_nodes_in_prompt = 500\n\n"
        "[ima]\nenabled = false\n\n[pipeline]\narchive_originals = true\n"
        "write_receipts = true\ncreate_gaps_automatically = true\n"
        "require_confirmation_for_new_node = true\n"
        "require_confirmation_for_any_current_view_change = true\n",
        encoding="utf-8",
    )
    cloud_profile = CloudProfile.demo()
    source_profile = SourceProfile(phase4_config, max_pdf_bytes=max_pdf_bytes)
    return {
        "config": config, "phase4_config": phase4_config, "cloud_profile": cloud_profile,
        "source_profile": source_profile,
        "service": SourceOperations(config, source_profile, cloud_profile),
        "prepared": prepared, "stage5_bytes": stage5, "stage6_bytes": stage6,
    }
