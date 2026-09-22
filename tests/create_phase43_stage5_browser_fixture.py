"""Create a disposable Company Material browser fixture; never use real databases."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multiformat_helpers import write_pdf
from workbench_stage7_fixture import stage7_fixture


async def chunks(body: bytes):
    yield body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Use a fresh output directory")
    case = stage7_fixture(output)
    config = case["config"]
    company_id, product_id = "NODE_STAGE5_BROWSER_COMPANY", "NODE_STAGE5_BROWSER_PRODUCT"
    with sqlite3.connect(config.knowledge_db) as connection:
        connection.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
            "VALUES(?,?,?,'Synthetic browser fixture','active','2026-09-22','2026-09-22')",
            [(company_id, "Stage Five Synthetic Company", "Company"),
             (product_id, "Stage Five Synthetic Product", "Product")],
        )
    source_ids = []
    for index, title in enumerate(("Synthetic official report", "Synthetic community note")):
        path = output / f"synthetic-material-{index}.pdf"
        write_pdf(path, [f"Stage Five Synthetic Company reported an update about Stage Five Synthetic Product in {index}."])
        source = asyncio.run(case["service"].upload(chunks(path.read_bytes()),
                            filename=path.name, mime_type="application/pdf"))
        source_ids.append(source["source_id"])
        case["service"].start(source["source_id"],
                              idempotency_key=f"stage5-browser-material-{index:04d}",
                              company_material_intent={
                                  "target_company_node_id": company_id,
                                  "material_kind": "earnings_report" if index == 0 else "community_material",
                                  "source_channel": "company_official" if index == 0 else "knowledge_community",
                                  "material_date": f"2026-09-{22-index:02d}", "operator_title": title,
                              })
    with sqlite3.connect(config.knowledge_db) as connection:
        connection.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,"
                           "ingestion_mode,publication_time,ingested_at) VALUES(?,?,?,?,?,'synthetic',?,?)",
                           (source_ids[0], "Canonical synthetic report", "synthetic.pdf", "synthetic",
                            case["service"].source(source_ids[0])["source_sha256"],
                            "2026-09-22", "2026-09-22"))
        connection.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) "
                           "VALUES('CLAIM_STAGE5_BROWSER','Synthetic Company reported a product update.',"
                           "'fact','2026-09-22',?,'2026-09-22')", (source_ids[0],))
        connection.execute("INSERT INTO source_node_links(source_id,node_id,role) VALUES(?,?,'subject')",
                           (source_ids[0], company_id))
        connection.executemany("INSERT INTO claim_node_links(claim_id,node_id,role) "
                               "VALUES('CLAIM_STAGE5_BROWSER',?,?)",
                               [(company_id, "subject"), (product_id, "context")])
    values = {"mode": config.mode, "knowledge_db": config.knowledge_db,
              "state_db": config.state_db, "artifact_root": config.artifact_root,
              "origin": "http://127.0.0.1:5173", "session_token_env": config.session_token_env}
    toml = "[workbench]\n" + "\n".join(
        f'{key} = {json.dumps(str(value).replace(chr(92), "/"))}' for key, value in values.items()
    ) + "\nremote = false\n"
    (output / "workbench.toml").write_text(toml, encoding="utf-8")
    (output / "fixture.json").write_text(json.dumps({"company_id": company_id,
        "product_id": product_id, "source_ids": source_ids}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"company_id": company_id, "product_id": product_id,
                      "source_ids": source_ids}))


if __name__ == "__main__":
    main()
