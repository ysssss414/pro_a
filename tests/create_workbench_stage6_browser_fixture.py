"""Create a fresh registered Stage 6 browser fixture and Workbench config."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))

from workbench_stage6_fixture import stage6_fixture


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--origin", default="http://127.0.0.1:5173")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Use a fresh output directory")
    case = stage6_fixture(output, origin=args.origin)
    config = case["config"]
    values = {
        "mode": config.mode,
        "knowledge_db": config.knowledge_db,
        "state_db": config.state_db,
        "artifact_root": config.artifact_root,
        "origin": config.origin,
        "session_token_env": config.session_token_env,
    }
    toml = "[workbench]\n" + "\n".join(
        f'{key} = {json.dumps(str(value).replace(chr(92), "/"))}' for key, value in values.items()
    ) + "\nremote = false\n"
    (output / "workbench.toml").write_text(toml, encoding="utf-8")
    result = {"artifact_id": case["artifact_id"], "config": str(output / "workbench.toml"),
              "origin": config.origin}
    (output / "fixture.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
