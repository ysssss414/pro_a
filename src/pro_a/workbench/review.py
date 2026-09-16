"""Native read DTO; evidence and typed capabilities remain byte-for-byte JSON values."""
from __future__ import annotations

import copy
import re

from .config import BoundaryError


def require_safe_projection(value):
    """Reject unsupported disclosure, never silently remove native evidence."""
    if isinstance(value, dict):
        for key, child in value.items():
            if re.search(r'(?:path|filename|file_name|secret|token|password|raw_response|raw_model|git_ref|repository_commit)', key, re.I):
                raise BoundaryError('PROJECTION_DISCLOSURE_FORBIDDEN')
            require_safe_projection(child)
    elif isinstance(value, list):
        for child in value:
            require_safe_projection(child)
    elif isinstance(value, str) and re.search(r'(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\|file://|(?:^|\s)/\S+|refs/(?:heads|tags)/)', value):
        raise BoundaryError('PROJECTION_DISCLOSURE_FORBIDDEN')


def project(packet: dict, validation: dict, artifact_id: str, packet_sha256: str, mode: str) -> dict:
    groups = ('claims', 'nodes', 'aliases', 'relations')
    items = [{key: copy.deepcopy(row[key]) for key in
              ('candidate_id', 'candidate_type', 'content', 'content_sha256', 'allowed_decisions', 'decision_effects')}
             for group in groups for row in packet[group]]
    summary = packet['summary']
    if len(items) != summary['total_operational_decisions_required']:
        raise BoundaryError('NATIVE_COUNT_MISMATCH')
    dto = {
        'artifact_id': artifact_id, 'packet_id': packet['packet_id'],
        'packet_file_sha256': packet_sha256,
        'immutable_packet_sha256': packet['immutable_packet_sha256'],
        'run_id': packet['run']['run_id'], 'mode': mode,
        'validation_state': validation['status'], 'packet_status': packet['packet_status'],
        'source': {key: packet['source'].get(key) for key in ('source_id', 'source_sha256', 'size_bytes', 'source_type')},
        'summary': copy.deepcopy(summary), 'items': items,
        'excluded_relation_inventory': copy.deepcopy(packet['excluded_relation_inventory']),
        'capabilities': {'read_only': True, 'decision_save_available': False,
                         'native_decisions_are_metadata_only': True},
    }
    require_safe_projection(dto)
    return dto
