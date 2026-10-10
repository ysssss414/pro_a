"""B0 diagnostic only: lexical provenance is NOT referent authorization.

No production imports this probe. A structurally valid graph below is not an
accepted graph: the negative antecedent test demonstrates the missing gate.
"""
from dataclasses import asdict

from pro_a.evidence_binding import identity, resolve_evidence_binding_v2, validate_catalog

VERSION = 'non-owning-context-lexical-probe-v1'


def require(value, code):
    if not value:
        raise ValueError(code)


def lexical_graph_probe(graph, catalog, context, nodes):
    validate_catalog(catalog, context)
    require(set(graph) == {'version', 'dispositions'} and graph['version'] == VERSION,
            'INVALID_GRAPH_SHAPE')
    rows = graph['dispositions']
    refs = tuple(u.evidence_ref for u in catalog.units)
    require(tuple(row['target_evidence_ref'] for row in rows) == refs, 'INCOMPLETE_GRAPH')
    dependencies = []
    edges = {}
    for row in rows:
        require(set(row) == {'target_evidence_ref', 'status', 'dependencies'}, 'INVALID_DISPOSITION')
        target = row['target_evidence_ref']
        status = row['status']
        require(status in ('NO_DEPENDENCY', 'DEPENDENCY', 'AMBIGUOUS_DEPENDENCY'), 'INVALID_STATUS')
        require(bool(row['dependencies']) == (status == 'DEPENDENCY'), 'INVALID_DEPENDENCIES')
        edges[target] = []
        for dep in row['dependencies']:
            require(set(dep) == {'kind', 'context_evidence_ref', 'target_selector',
                    'context_selector', 'resolved_node_id'}, 'INVALID_DEPENDENCY_SHAPE')
            require(dep['kind'] == 'REFERENT_RESOLUTION', 'UNSUPPORTED_KIND')
            foreign = dep['context_evidence_ref']
            require(foreign in refs and foreign != target, 'INVALID_CONTEXT_REF')
            bindings = [resolve_evidence_binding_v2({'evidence_ref': ref, 'evidence_selector': selector},
                catalog, context) for ref, selector in ((target, dep['target_selector']),
                                                        (foreign, dep['context_selector']))]
            target_binding, context_binding = bindings
            matches = [n for n in nodes if n['node_id'] == dep['resolved_node_id']
                       and dep['resolved_node_id'] in context.known_node_ids
                       and context_binding.evidence_excerpt in (n['canonical_name'], *n['aliases'])]
            require(len(matches) == 1, 'INVALID_RESOLVED_NODE')
            ctx_basis = {'version': VERSION, 'source_sha': context.source_sha256,
                'piece_id': context.piece.piece_id, 'piece_sha': context.piece.source_sha256,
                'span': [context_binding.source_start, context_binding.source_end],
                'text_sha': context_binding.raw_excerpt_sha256, 'kind': dep['kind']}
            item = {'kind': dep['kind'], 'target_ref': target,
                'target_binding': asdict(target_binding), 'context_binding': asdict(context_binding),
                'context_id': 'CTX_' + identity(ctx_basis).upper(),
                'resolved_node_id': dep['resolved_node_id']}
            item['dependency_id'] = 'DEP_' + identity(item).upper()
            dependencies.append(item)
            edges[target].append(foreign)
    def visit(ref, active, done):
        require(ref not in active, 'CIRCULAR_DEPENDENCY')
        if ref not in done:
            for foreign in edges[ref]:
                visit(foreign, active | {ref}, done)
            done.add(ref)
    done = set()
    for ref in refs:
        visit(ref, set(), done)
    require(len({d['dependency_id'] for d in dependencies}) == len(dependencies), 'DUPLICATE_DEPENDENCY')
    return {'graph_id': 'GRAPH_' + identity(graph).upper(), 'dependencies': dependencies,
            'semantic_authorization': 'UNPROVEN'}


def project(graph, assigned_refs, catalog):
    owned = set(assigned_refs)
    return {'owned': [{'evidence_ref': u.evidence_ref, 'text': u.exact_text}
                     for u in catalog.units if u.evidence_ref in owned],
        'context': [{'context_id': d['context_id'], 'dependency_id': d['dependency_id'],
            'kind': d['kind'], 'target_evidence_ref': d['target_ref'],
            'target_selector': d['target_binding']['evidence_excerpt'],
            'context_selector': d['context_binding']['evidence_excerpt'],
            'resolved_node_id': d['resolved_node_id']} for d in graph['dependencies']
                    if d['target_ref'] in owned]}


def exact_substitution_probe(statement, unit, dependency):
    """Proves only a lexical delta; not that the resolver selected the right Node."""
    require(dependency['target_ref'] == unit.evidence_ref, 'WRONG_TARGET')
    target = dependency['target_binding']['evidence_excerpt']
    context = dependency['context_binding']['evidence_excerpt']
    require(unit.exact_text.count(target) == 1, 'AMBIGUOUS_TARGET')
    require(statement == unit.exact_text.replace(target, context, 1), 'UNAUTHORIZED_STATEMENT_DELTA')


def direct_refs_probe(refs, assigned_refs):
    require(all(ref.startswith('EV_') and ref in assigned_refs for ref in refs), 'NON_OWNED_PRIMARY_EVIDENCE')
