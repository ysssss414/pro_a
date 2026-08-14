from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .analyzer import Analyzer
from .audit import build_source_audit
from .config import load_config
from .db import Database
from .ima import IMAClient
from .impact_recovery import ImpactRecoveryService
from .pipeline import IngestionPipeline
from .proposals import ProposalManager
from .receipts import write_proposal
from .storage import ensure_workspace


def jprint(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pro-a", description="pro_a research knowledge engine")
    p.add_argument("--config", default="config.toml")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create workspace and SQLite schema")

    ingest = sub.add_parser("ingest", help="Process Inbox")
    ingest.add_argument("--once", action="store_true", help="Process currently stable files once")

    watch = sub.add_parser("watch", help="Poll Inbox continuously")
    watch.add_argument("--interval", type=float, default=5.0)

    status = sub.add_parser("status", help="Show local knowledge-engine status")

    source = sub.add_parser("source", help="Inspect one Source without changing it")
    ssub = source.add_subparsers(dest="source_command", required=True)
    source_show = ssub.add_parser("show")
    source_show.add_argument("source_id")

    nodes = sub.add_parser("nodes")
    nsub = nodes.add_subparsers(dest="nodes_command", required=True)
    nsub.add_parser("list")
    seed = nsub.add_parser("seed")
    seed.add_argument("csv_path")
    add = nsub.add_parser("add")
    add.add_argument("name")
    add.add_argument("type")
    add.add_argument("--aliases", default="")
    add.add_argument("--description", default="")

    rel = sub.add_parser("relations")
    rsub = rel.add_subparsers(dest="relations_command", required=True)
    rlist = rsub.add_parser("list")
    rlist.add_argument("--node-id", default="")
    radd = rsub.add_parser("add")
    radd.add_argument("from_node_id")
    radd.add_argument("relation_type")
    radd.add_argument("to_node_id")
    radd.add_argument("--scope", default="")
    rseed = rsub.add_parser("seed")
    rseed.add_argument("csv_path")

    props = sub.add_parser("proposals")
    psub = props.add_subparsers(dest="proposal_command", required=True)
    psub.add_parser("list")
    show = psub.add_parser("show")
    show.add_argument("proposal_id")
    accept = psub.add_parser("accept")
    accept.add_argument("proposal_id")
    reject = psub.add_parser("reject")
    reject.add_argument("proposal_id")
    reject.add_argument("--reason", default="")

    impacts = sub.add_parser("impacts", help="Inspect and recover persisted Impact Reviews")
    impact_sub = impacts.add_subparsers(dest="impact_command", required=True)
    impact_show = impact_sub.add_parser("show")
    impact_show.add_argument("impact_id")
    impact_retry = impact_sub.add_parser("retry")
    impact_retry.add_argument("impact_id")
    impact_retry.add_argument("--max-repairs", type=int, choices=(1, 2), default=2)

    ima = sub.add_parser("ima")
    isub = ima.add_subparsers(dest="ima_command", required=True)
    isub.add_parser("list-kbs")

    return p


def _ctx(args):
    cfg = load_config(args.config)
    ensure_workspace(cfg.root)
    db = Database(cfg.db_path)
    db.init_schema()
    analyzer = Analyzer(cfg, db)
    return cfg, db, analyzer


def main(argv: list[str] | None = None):
    args = build_parser().parse_args(argv)
    cfg, db, analyzer = _ctx(args)

    if args.command == "init":
        print(f"Initialized: {cfg.root}")
        print(f"Database: {cfg.db_path}")
        return

    if args.command == "ingest":
        pipeline = IngestionPipeline(cfg, db)
        results = pipeline.process_all()
        jprint(results)
        if any(result.get("status") == "failed" for result in results):
            raise SystemExit(1)
        return

    if args.command == "watch":
        pipeline = IngestionPipeline(cfg, db)
        print(f"Watching {cfg.root / 'inbox'} every {args.interval}s. Ctrl+C to stop.")
        try:
            while True:
                results = pipeline.process_all()
                if results:
                    jprint(results)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Stopped.")
        return

    if args.command == "status":
        jprint({
            "workspace": str(cfg.root),
            "sources": db.one("SELECT COUNT(*) AS n FROM sources")["n"],
            "nodes": db.one("SELECT COUNT(*) AS n FROM nodes")["n"],
            "claims": db.one("SELECT COUNT(*) AS n FROM claims")["n"],
            "current_views": db.one("SELECT COUNT(*) AS n FROM current_views WHERE status='official'")["n"],
            "pending_proposals": db.one("SELECT COUNT(*) AS n FROM proposals WHERE status='pending'")["n"],
            "open_gaps": db.one("SELECT COUNT(*) AS n FROM knowledge_gaps WHERE status IN ('open','reopened','needs_refresh')")["n"],
            "llm_available": analyzer.available,
            "ima_available": IMAClient(cfg.ima).available,
        })
        return

    if args.command == "source":
        if args.source_command == "show":
            try:
                jprint(build_source_audit(db, args.source_id))
            except KeyError as exc:
                raise SystemExit(f"Source not found: {args.source_id}") from exc
        return

    if args.command == "nodes":
        if args.nodes_command == "list":
            jprint(db.list_nodes())
        elif args.nodes_command == "seed":
            count = db.seed_nodes_csv(Path(args.csv_path))
            print(f"Seeded {count} new nodes")
        elif args.nodes_command == "add":
            aliases = [x.strip() for x in args.aliases.split("|") if x.strip()]
            node_id = db.add_node(args.name, args.type, aliases, args.description)
            print(node_id)
        return

    if args.command == "relations":
        if args.relations_command == "list":
            if args.node_id:
                jprint(db.neighbors(args.node_id))
            else:
                jprint(db.all("SELECT * FROM node_relations ORDER BY created_at"))
        elif args.relations_command == "add":
            rel_id = db.add_relation(args.from_node_id, args.relation_type, args.to_node_id, scope=args.scope)
            print(rel_id)
        elif args.relations_command == "seed":
            try:
                count = db.seed_relations_csv(Path(args.csv_path))
            except (OSError, ValueError) as exc:
                raise SystemExit(f"Relation seed failed: {exc}") from exc
            print(f"Seeded {count} new relations")
        return

    if args.command == "proposals":
        manager = ProposalManager(cfg, db, analyzer)
        if args.proposal_command == "list":
            rows = db.pending_proposals()
            for r in rows:
                r["payload"] = json.loads(r["payload_json"])
                r.pop("payload_json", None)
            jprint(rows)
        elif args.proposal_command == "show":
            proposal = db.proposal(args.proposal_id)
            if not proposal:
                raise SystemExit(f"Not found: {args.proposal_id}")
            jprint(proposal)
        elif args.proposal_command == "accept":
            jprint(manager.accept(args.proposal_id))
        elif args.proposal_command == "reject":
            manager.reject(args.proposal_id, args.reason)
            print("rejected")
        return

    if args.command == "impacts":
        recovery = ImpactRecoveryService(cfg, db, analyzer)
        try:
            if args.impact_command == "show":
                jprint(recovery.show(args.impact_id))
            elif args.impact_command == "retry":
                jprint(recovery.retry(args.impact_id, max_repairs=args.max_repairs))
        except KeyError as exc:
            raise SystemExit(f"Impact not found: {args.impact_id}") from exc
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        return

    if args.command == "ima":
        client = IMAClient(cfg.ima)
        if args.ima_command == "list-kbs":
            jprint(client.list_addable_kbs())
        return

    raise SystemExit(2)


if __name__ == "__main__":
    main()
