from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat
import tomllib
from urllib.parse import urlsplit

from pro_a.foundation_schema_preparation import require_execution_schema
from pro_a.query import ReadOnlyQuery


class BoundaryError(ValueError):
    """Messages are fixed codes, safe for operator and HTTP responses."""


def checked_path(path: Path, *, missing: bool = False) -> Path:
    """Inspect lexical ancestors before resolution (including Windows reparse points)."""
    if '..' in path.parts:
        raise BoundaryError('UNSAFE_PATH')
    path = path.absolute()
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise BoundaryError('PATH_UNAVAILABLE') from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise BoundaryError('LINK_FORBIDDEN')
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise BoundaryError('HARDLINK_FORBIDDEN')
    return path.resolve()


@dataclass(frozen=True)
class WorkbenchConfig:
    mode: str
    knowledge_db: Path
    state_db: Path
    artifact_root: Path
    origin: str
    session_token_env: str = 'PRO_A_WORKBENCH_TOKEN'
    remote: bool = False

    @classmethod
    def load(cls, path: Path) -> 'WorkbenchConfig':
        raw = tomllib.loads(path.read_text(encoding='utf-8'))['workbench']
        for key in ('knowledge_db', 'state_db', 'artifact_root'):
            raw[key] = path.absolute().parent / raw[key]
        config = cls(**raw)
        config.validate()
        return config

    def validate(self) -> None:
        if self.mode not in ('PRIVATE', 'DEMO'):
            raise BoundaryError('MODE_INVALID')
        origin = urlsplit(self.origin)
        if origin.scheme not in ('http', 'https') or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment:
            raise BoundaryError('ORIGIN_INVALID')
        if self.remote and origin.scheme != 'https':
            raise BoundaryError('REMOTE_REQUIRES_HTTPS')
        if not self.remote and origin.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise BoundaryError('LOCAL_ORIGIN_REQUIRED')
        knowledge = checked_path(self.knowledge_db)
        state = checked_path(self.state_db, missing=True)
        artifacts = checked_path(self.artifact_root, missing=True)
        if state == knowledge or knowledge.is_relative_to(artifacts) or state.is_relative_to(artifacts) or artifacts.is_relative_to(state.parent) or knowledge.is_relative_to(state.parent):
            raise BoundaryError('STATE_NOT_ISOLATED')
        self.check_knowledge()

    def check_knowledge(self) -> None:
        """No Database/init_schema: existing 0.2.3 contract or fail closed."""
        try:
            path = checked_path(self.knowledge_db)
            with ReadOnlyQuery(path).connect() as connection:
                require_execution_schema(connection)
                marker = connection.execute("SELECT value FROM meta WHERE key='workbench_fixture_kind'").fetchone()
                synthetic = marker is not None and marker[0] == 'SYNTHETIC_PUBLIC_SAFE'
                if synthetic != (self.mode == 'DEMO'):
                    raise BoundaryError('KNOWLEDGE_MODE_MISMATCH')
        except BoundaryError:
            raise
        except Exception:
            raise BoundaryError('KNOWLEDGE_SCHEMA_UNAVAILABLE') from None

    def bindings(self) -> dict:
        return {'schema_version': '1', 'mode': self.mode,
                'knowledge_db': str(self.knowledge_db.resolve()),
                'artifact_root': str(self.artifact_root.resolve())}
