from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass
class WorkspaceConfig:
    root: Path = Path("./workspace")
    settle_seconds: int = 2


@dataclass
class LLMConfig:
    enabled: bool = False
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "PROA_LLM_API_KEY"
    model: str = "deepseek-chat"
    timeout_seconds: int = 120
    temperature: float = 0.1
    max_output_tokens: int = 8192
    max_chunk_chars: int = 22000
    max_nodes_in_prompt: int = 500

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "")


@dataclass
class IMAConfig:
    enabled: bool = False
    base_url: str = "https://ima.qq.com"
    client_id_env: str = "IMA_OPENAPI_CLIENTID"
    api_key_env: str = "IMA_OPENAPI_APIKEY"
    source_kb_id: str = ""
    source_folder_id: str = ""
    output_kb_id: str = ""
    output_folder_id: str = ""
    upload_originals: bool = True
    upload_current_views: bool = True
    skip_same_name: bool = True

    @property
    def client_id(self) -> str:
        return os.getenv(self.client_id_env, "")

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "")


@dataclass
class PipelineConfig:
    archive_originals: bool = True
    write_receipts: bool = True
    create_gaps_automatically: bool = True
    require_confirmation_for_new_node: bool = True
    require_confirmation_for_any_current_view_change: bool = True


@dataclass
class AppConfig:
    workspace: WorkspaceConfig
    llm: LLMConfig
    ima: IMAConfig
    pipeline: PipelineConfig
    config_path: Path

    @property
    def root(self) -> Path:
        return self.workspace.root.resolve()

    @property
    def db_path(self) -> Path:
        return self.root / "pro_a.db"


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def load_config(path: str | Path = "config.toml") -> AppConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}. Copy config.example.toml to config.toml first.")
    with path.open("rb") as f:
        data = tomllib.load(f)

    w = _section(data, "workspace")
    l = _section(data, "llm")
    i = _section(data, "ima")
    p = _section(data, "pipeline")

    root = Path(w.get("root", "./workspace"))
    if not root.is_absolute():
        root = (path.parent / root).resolve()

    return AppConfig(
        workspace=WorkspaceConfig(root=root, settle_seconds=int(w.get("settle_seconds", 2))),
        llm=LLMConfig(**{k: v for k, v in l.items() if k in LLMConfig.__dataclass_fields__}),
        ima=IMAConfig(**{k: v for k, v in i.items() if k in IMAConfig.__dataclass_fields__}),
        pipeline=PipelineConfig(**{k: v for k, v in p.items() if k in PipelineConfig.__dataclass_fields__}),
        config_path=path.resolve(),
    )
