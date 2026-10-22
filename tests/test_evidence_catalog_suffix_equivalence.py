"""The gate-performance fix must preserve every catalog span and identity."""
import re

import pytest

from pro_a import source_analysis_wire as wire
from test_source_analysis_wire import context


@pytest.mark.parametrize('text',[
    'U.S. capacity rose. Dr. Li states 1.5 units. A. example.',
    'Alpha.\nBeta 2.\n\n中文。\n尾部 Q.',
    'ABC\n. Next. ABC\r\n. Done.',
    'Product_123. product-ABC. αβγ. 2027. End.',
    'A'*3000+'?'+'. Next statement.',
    '[[PAGE:1]]\nQ: A.B.C. roadmap?\nA: supply rose.\n[[PAGE:2]]\n2027年规划。',
])
def test_exact_catalog_matches_previous_suffix_search(monkeypatch,text):
    ctx=context(text)
    current=wire.build_source_evidence_catalog(ctx)
    original_search=re.search
    def previous(pattern,string,*args,**kwargs):
        if pattern==r'(?<![A-Za-z.])([A-Za-z.]+)$':pattern=r'([A-Za-z.]+)$'
        return original_search(pattern,string,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(wire.re,'search',previous)
        legacy=wire.build_source_evidence_catalog(ctx)
    assert current==legacy
