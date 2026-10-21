"""Explicit continuous original-page selection; exact text, no document rewriting."""
from dataclasses import asdict
import hashlib
from importlib.metadata import version
from pathlib import Path
import re

from .evidence_binding import identity

VERSION = 'continuous-source-range-v1'
PLANNER = 'continuous-range-native-planner-v1'


def require(value, code):
    if not value:
        raise ValueError(code)


def text_sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def select(parsed, source_sha256, first_page, last_page):
    from .parsers import semantic_eligible_source_text
    text = semantic_eligible_source_text(parsed)
    require(type(first_page) is int and type(last_page) is int
            and 1 <= first_page <= last_page, 'SOURCE_SCOPE_PAGES_INVALID')
    markers = list(re.finditer(r'\[\[PAGE:(\d+)\]\]', text))
    numbers = [int(m[1]) for m in markers]
    require(numbers == list(range(1, len(numbers) + 1)), 'SOURCE_SCOPE_PAGE_MARKERS_AMBIGUOUS')
    require(last_page <= len(markers), 'SOURCE_SCOPE_PAGE_OUT_OF_RANGE')
    start = markers[first_page - 1].start()
    end = markers[last_page].start() if last_page < len(markers) else len(text)
    require(start < end, 'SOURCE_SCOPE_EMPTY')
    root = Path(__file__).parent
    parser = {'parsed_text_sha256': text_sha(parsed.text),
        'segments_sha256': identity([asdict(s) for s in (parsed.segments or ())]),
        'diagnostics_sha256': identity(parsed.diagnostics),
        'components': {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
                       for n in ('parsers.py', 'pdf_layout.py', 'analyzer.py',
                                 'table_claim_safety.py', 'source_scope.py')},
        'packages': {n: version(n) for n in ('pypdf', 'pymupdf', 'pymupdf-layout')}}
    return {'version': VERSION, 'planner': PLANNER, 'source_sha256': source_sha256,
        'parser_identity': parser, 'semantic_text_sha256': text_sha(text),
        'original_chars': len(text), 'first_page': first_page, 'last_page': last_page,
        'global_start': start, 'global_end': end, 'range_sha256': text_sha(text[start:end]),
        'coordinate_system': 'UNICODE_CODEPOINTS_HALF_OPEN_IN_SEMANTIC_ELIGIBLE_ORIGINAL',
        'local_to_original': 'global_start + local_offset', 'coverage': 'SELECTED_RANGE_ONLY'}


def validate_parsed(parsed, source_sha256, selection):
    require(selection == select(parsed, source_sha256, selection['first_page'], selection['last_page']),
            'SOURCE_SCOPE_PARSE_OR_SOURCE_DRIFT')


def slice_text(text, selection):
    require(selection['version'] == VERSION and selection['planner'] == PLANNER
            and text_sha(text) == selection['semantic_text_sha256']
            and len(text) == selection['original_chars'], 'SOURCE_SCOPE_TEXT_DRIFT')
    start, end = selection['global_start'], selection['global_end']
    require(type(start) is int and type(end) is int and 0 <= start < end <= len(text),
            'SOURCE_SCOPE_RANGE_INVALID')
    result = text[start:end]
    require(text_sha(result) == selection['range_sha256'], 'SOURCE_SCOPE_RANGE_DRIFT')
    pages = [int(n) for n in re.findall(r'\[\[PAGE:(\d+)\]\]', result)]
    require(pages == list(range(selection['first_page'], selection['last_page'] + 1)),
            'SOURCE_SCOPE_PAGE_RANGE_MISMATCH')
    return result


def validate_piece(native, source_sha256, piece):
    selection = native.get('source_scope')
    if not piece.scope_identity:
        require(selection is None, 'SOURCE_SCOPE_UNBOUND')
        return
    require(type(selection) is dict and selection['version'] == VERSION
            and selection['source_sha256'] == source_sha256
            and identity(selection) == piece.scope_identity
            and text_sha(piece.source_text) == selection['range_sha256']
            and len(piece.source_text) == selection['global_end'] - selection['global_start'],
            'SOURCE_SCOPE_PIECE_DRIFT')


def original_range(selection, local_start, local_end):
    require(type(local_start) is int and type(local_end) is int
            and 0 <= local_start < local_end <= selection['global_end'] - selection['global_start'],
            'SOURCE_SCOPE_EVIDENCE_OUT_OF_RANGE')
    return selection['global_start'] + local_start, selection['global_start'] + local_end
