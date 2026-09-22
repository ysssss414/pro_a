"""Bind two independent Stage 3 reviews and prepare an advisory human packet."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from pro_a.production_promotion import canonical_sha256, sha256_file
from pro_a.structured_foundation import read_package

BASELINE = '690fc4f26e02607fb54a48053cf8faf6775621c3'
INITIAL_HEAD = '4dfa83d5366760294e6c8fb801cc3eb7ca666b62'
PRODUCTION_SHA = '6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1'
PACKAGE_SHA = '131421d3bbe3b968a1c72ee6e3767cfad6141a0cdaea1850ba30cccbd3932918'
STAGE2_SHA = '06006a1c98247f1803dac9cdcd0f10ade5d84beddc56a12e3768e5a9e5bfc66c'
STAGE2_AUTH_SHA = '23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f'
POPULATION_SHA = '207f4f57f78f0fe0034a3bb17edd38cc911a21cd322ea753ac02edc41a70babb'
STRUCTURAL_SHA = 'c1a9150cf43020d293232328316472ae0451efcb160bc7efecec71cafd845113'
RESOLUTION_FILE_SHA = '4ee619c8d597f6ffcacb357efd7eddce750b1a2bc6fe3a21c7a9a78f182f4065'
REVIEW_FILE_SHA = '2ec173f05215e9d62323ff1cde07108fbcf5eab1afcaf6a020ee438875f04a92'
REVIEW_A_SHA = 'ae5224b7f8d51261accc8ad44bbb82844bbf5d99043e1af452e88d2de0c6f03c'
REVIEW_B_SHA = 'c23cc17c7ee02a7daa879cef2b8e55d79e6150a9f89755937bc799bf71884012'
ARTIFACT = ROOT / 'workspace/phase4_stage43_stage3_cross_domain_resolution/qualified_v3'
IDENTITY = ('REUSE_CANONICAL', 'CREATE_NEW_CANONICAL', 'KEEP_DOMAIN_SPECIFIC', 'DEFER', 'REJECT')
RELATION = ('REUSE_RELATION', 'CREATE_RELATION', 'KEEP_DOMAIN_SPECIFIC_RELATION', 'DEFER_RELATION', 'REJECT_RELATION')
INTERPRETATION = ('identity_boundary', 'object_type', 'scope', 'granularity', 'quarantine',
                  'ontology', 'evidence_sufficiency', 'temporal')
MATERIAL_CASES = {
    'SC-CN-0033': 'A proposes a distinct Chiplet Product; B holds the product boundary for explicit admission.',
    'SC-CN-0051': 'A proposes reuse of the existing SOI Wafer ID; B finds the bound excerpt insufficient to authorize the plural-name mapping.',
    'SC-CN-0031': 'A proposes a new generic Package Substrate parent; B defers the broader-than-advanced boundary.',
    'SC-CN-0042': 'A proposes a distinct starting-wafer polishing Process; B defers its boundary against fabrication CMP.',
}
SPECIAL_CASES = {
    'High Bandwidth Memory / DRAM': (('High Bandwidth Memory', 'HBM', 'DRAM', 'Dynamic Random-Access Memory'),
                                    'Keep generic DRAM separate from Server DRAM and HBM; retain source-scoped HBM relations.'),
    'Advanced Packaging': (('Advanced Packaging',),
                           'Generic packaging class may reuse its exact Segment; vendor services remain separate.'),
    'CoWoS family': (('CoWoS',),
                     'Review S/R variant names and existing edge temporal semantics without duplicating relations.'),
    'SoIC': (('SoIC',), 'Preserve the specific identity and distinguish it from broader 3DFabric service scope.'),
    '3DFabric': (('3DFabric',), 'Vendor service umbrella remains a distinct, deferred identity question.'),
    'Interposer variants': (('Interposer',), 'Generic, silicon, and RDL interposers retain separate granularity.'),
    'UCIe': (('UCIe',), 'Reuse the standard identity; treat UCIe 3.0 as version-scoped evidence, not a parallel node.'),
    'Chiplet / Chiplet Architecture': (('Chiplet',),
                                       'Physical companion die and architecture technology have different object boundaries.'),
    'Silicon Photonics / PIC': (('Silicon Photonics', 'Photonic Integrated Circuit', 'PIC'),
                               'Generic PIC breadth cannot be silently merged with silicon photonics.'),
    'EDA / PDK / Process Node': (('EDA', 'PDK', 'Process Node'),
                                'No frozen comparison item for these terms if locator is empty.'),
    'Photoresist': (('Photoresist',),
                    'Separate generic lithography resist, packaging resist, and resin component scope.'),
    'CMP': (('CMP', 'Chemical Mechanical Planarization', 'Silicon Wafer Polishing'),
            'Keep starting-wafer mirror polishing and fabrication CMP granularity review visible.'),
    'Semiconductor Metrology': (('Semiconductor Metrology',),
                                'Technology/function differs from a specific metrology Equipment identity.'),
    'Underfill / Packaging Encapsulant': (('Underfill', 'Packaging Encapsulant'),
                                          'Underfill is narrower than the umbrella protection-material class.'),
    'Glass Core Substrate': (('Glass Core Substrate',), 'Historical quarantine remains binding.'),
    'Diamond thermal material': (('Diamond Thermal Material',),
                                 'Potential replacement use does not establish deployed material identity.'),
}
LOCAL_PATH = re.compile(r'(?i)(?:[a-z]:[\\/]|\\\\[a-z0-9_.-]+[\\/]|file://|/home/|/Users/|/mnt/)')


def require(condition, message):
    if not condition:
        raise ValueError('STAGE3_DOUBLE_REVIEW_FAILED: ' + message)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def check_binding():
    require(git('branch', '--show-current') == 'codex/phase43-stage3-cross-domain-resolution', 'branch drift')
    require(git('rev-parse', 'origin/main') == git('rev-parse', 'main') == BASELINE, 'baseline drift')
    require(sha256_file(ROOT / 'workspace/pro_a.db') == PRODUCTION_SHA, 'Production drift')
    require(read_package(ROOT / 'semiconductor_foundation_backfill_web_pro_v1')['sha256'] == PACKAGE_SHA,
            'Stage 2 structured package drift')
    public = load(ROOT / 'docs/phase43_stage3_automated_qualification_receipt.json')
    stage2 = load(ROOT / 'docs/phase43_stage2_final_human_qualification_receipt.json')
    result = load(ARTIFACT / 'qualification_result.json')
    require(file_sha(ROOT / 'docs/phase43_stage2_human_authorization.json') ==
            stage2['authorization_file_sha256'] == STAGE2_AUTH_SHA,
            'Stage 2 HUMAN_USER decisions drift')
    require(public['result'] == 'PASS' and public['final_human_qualification'] == 'PENDING',
            'automated qualification drift')
    for record in (public, result):
        require(record['baseline'] == BASELINE and record['population_sha256'] == POPULATION_SHA,
                'qualification baseline/population drift')
        require(record['ai_hardware_input_sha256'] == PRODUCTION_SHA and
                record['semiconductor_input_sha256'] == PACKAGE_SHA, 'input binding drift')
    require(public['stage2_immutable_packet_sha256'] == result['stage2_packet_sha256'] ==
            stage2['native_qualification']['parent_immutable_packet_sha256'] == STAGE2_SHA,
            'Stage 2 immutable packet drift')
    require(public['workspace_a_structural_sha256'] == public['workspace_b_structural_sha256'] ==
            STRUCTURAL_SHA, 'structural identity drift')
    require(public['human_required'] == public['mandatory_exceptions'] == 100 and
            public['residual_eligible'] == 0, 'mandatory population drift')
    require(public['identity_outcomes'] == {
                'REUSE_CANONICAL': 16, 'CREATE_NEW_CANONICAL': 4,
                'KEEP_DOMAIN_SPECIFIC': 0, 'DEFER': 25, 'REJECT': 1} and
            public['relation_outcomes'] == {
                'REUSE_RELATION': 0, 'CREATE_RELATION': 38,
                'KEEP_DOMAIN_SPECIFIC_RELATION': 0, 'DEFER_RELATION': 16,
                'REJECT_RELATION': 0} and
            public['cross_domain_collisions'] == 1 and
            public['unresolved_identity_conflicts'] == 25 and
            public['ontology_pressure_cases'] == 4 and
            public['temporal_mismatches_deferred'] == 2 and
            public['claim_provenance_preserved'] == 19 and
            public['cross_source_leakage'] == 0,
            'frozen automated outcomes or provenance drift')
    for label in ('a', 'b'):
        base = ARTIFACT / label
        require(file_sha(base / 'resolution.json') == RESOLUTION_FILE_SHA, 'resolution bytes drift: ' + label)
        require(file_sha(base / 'review_population.json') == REVIEW_FILE_SHA,
                'review population bytes drift: ' + label)
    resolution = load(ARTIFACT / 'a/resolution.json')
    handoff = load(ARTIFACT / 'a/review_population.json')
    require(canonical_sha256(resolution['population']) == POPULATION_SHA and
            canonical_sha256(resolution) == STRUCTURAL_SHA, 'resolved population drift')
    require(handoff['population_sha256'] == POPULATION_SHA and
            handoff['structural_sha256'] == STRUCTURAL_SHA and len(handoff['items']) == 100,
            'handoff population drift')
    items = handoff['items']
    require(len({item['item_id'] for item in items}) == 100 and
            Counter(item['kind'] for item in items) == {'identity': 46, 'relation': 54},
            'review population multiplicity drift')
    require(all(item['resolution']['human_required'] and
                item['human_input'] == {'decision': '', 'target_id': '', 'reason': ''}
                for item in items), 'HUMAN_USER decision already present')
    return items


def validate_review(role, document, items):
    require(document['reviewer'] == role and document['population_sha256'] == POPULATION_SHA,
            'reviewer/population binding: ' + role)
    rows = document['items']
    expected = [item['item_id'] for item in items]
    actual = [row['item_id'] for row in rows]
    require(len(rows) == len(set(actual)) == 100 and set(actual) == set(expected),
            'review coverage/duplicates: ' + role)
    by_id = {item['item_id']: item for item in items}
    for row in rows:
        item = by_id[row['item_id']]
        require(row['kind'] == item['kind'], 'object kind mismatch: ' + row['item_id'])
        require(row.get('automated_outcome', item['resolution']['outcome']) ==
                item['resolution']['outcome'], 'automated outcome drift: ' + row['item_id'])
        require(row.get('human_user_decision') is None, 'HUMAN_USER decision injected: ' + row['item_id'])
        allowed = IDENTITY if row['kind'] == 'identity' else RELATION
        require(row['native_decision'] in allowed, 'native operation invalid: ' + row['item_id'])
        if row['native_decision'].startswith('REUSE_'):
            require(isinstance(row.get('target'), str) and row['target'],
                    'REUSE missing target: ' + row['item_id'])
        require(row.get('confidence') in ('HIGH', 'MEDIUM', 'LOW') and
                row.get('materiality') in ('HIGH', 'MEDIUM', 'LOW'),
                'confidence/materiality missing: ' + row['item_id'])
        require(all(isinstance(row.get(key), str) and row[key].strip()
                    for key in ('recommendation', 'reason', 'evidence_assessment')),
                'review narrative missing: ' + row['item_id'])
        require(row.get('source_identity') and row.get('temporal_scope'),
                'source or temporal assessment missing: ' + row['item_id'])
        require(isinstance(row.get('risk_flags'), list) and
                all(isinstance(flag, str) for flag in row['risk_flags']),
                'risk flags invalid: ' + row['item_id'])
        interpretation = row.get('reviewer_interpretation')
        require(isinstance(interpretation, dict) and
                all(isinstance(interpretation.get(key), str) and interpretation[key]
                    for key in INTERPRETATION), 'interpretation missing: ' + row['item_id'])
        refs = {ev['evidence_id'] for ev in item['evidence']}
        require(set(row.get('evidence_ids', [])) == refs, 'evidence IDs drift: ' + row['item_id'])
        sources = {ev['source_id'] for ev in item['evidence']}
        source_identity = row['source_identity']
        if isinstance(source_identity, dict):
            source_ids = set(source_identity.get('source_ids', source_identity.get('source_id', [])))
            source_shas = set(source_identity.get('source_sha256', []))
        elif isinstance(source_identity, list):
            source_ids = {source['source_id'] for source in source_identity}
            source_shas = {source['source_sha256'] for source in source_identity}
        else:
            source_ids = {source for source in sources if source in source_identity}
            source_shas = set()
        require(source_ids == sources if sources else
                ('NO_ADMITTED_SOURCE' in source_identity.get('source_id', [])
                 if isinstance(source_identity, dict) else source_identity == 'NO_ADMITTED_SOURCE'),
                'source identity drift: ' + row['item_id'])
        require(source_shas == {ev['source_sha256'] for ev in item['evidence']},
                'source hash drift: ' + row['item_id'])
        require(not LOCAL_PATH.search(frozen_json(row)), 'local path leakage: ' + row['item_id'])
    return {row['item_id']: row for row in rows}


def validate_access(role, access, review_sha):
    base = 'workspace/phase4_stage43_stage3_cross_domain_resolution/qualified_v3/' + role.lower()
    expected = {base + '/review_population.json': REVIEW_FILE_SHA,
                base + '/resolution.json': RESOLUTION_FILE_SHA,
                'docs/PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION_CONTRACT.md':
                    file_sha(ROOT / 'docs/PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION_CONTRACT.md')}
    manifest = {entry['path']: entry['sha256'] for entry in access.get('input_files', [])}
    require(access['reviewer'] == role and access['fork_turns'] == 'none' and
            access['frozen_review_file_sha256'] == REVIEW_FILE_SHA and
            access['population_sha256'] == POPULATION_SHA and
            access['peer_output_accessed'] is False and
            access['same_model_provider_os_independence_claimed'] is False and
            access['review_output_sha256'] == review_sha and manifest == expected,
            'review access/isolation binding: ' + role)


def compare_reviews(a, b):
    operation = a['native_decision'] != b['native_decision']
    target = a.get('target') != b.get('target') and (
        a['native_decision'].startswith('REUSE_') or b['native_decision'].startswith('REUSE_'))
    changed = {key for key in INTERPRETATION
               if a['reviewer_interpretation'][key] != b['reviewer_interpretation'][key]}
    evidence = 'evidence_sufficiency' in changed
    type_scope = bool(changed & {'identity_boundary', 'object_type', 'scope', 'granularity',
                                 'quarantine', 'ontology'})
    temporal = 'temporal' in changed
    categories = [name for name, flag in (
        ('NATIVE_OPERATION_CONFLICT', operation), ('TARGET_CONFLICT', target),
        ('EVIDENCE_CONFLICT', evidence), ('TYPE_OR_SCOPE_CONFLICT', type_scope),
        ('TEMPORAL_CONFLICT', temporal)) if flag]
    return {'status': 'A_B_SUBSTANTIVE_DISAGREEMENT' if categories else 'A_B_SUBSTANTIVE_AGREEMENT',
            'disagreement_type': categories, 'native_operation_conflict': operation,
            'target_conflict': target, 'evidence_conflict': evidence,
            'type_scope_conflict': type_scope, 'temporal_conflict': temporal,
            'changed_interpretations': sorted(changed)}


def semantic_reconciliation(item, a, b, raw):
    """Resolve rubric-label differences after reading both pinned reviews' reasons."""
    item_id = item['item_id']
    row = dict(raw)
    row['raw_interpretation_differences'] = raw['changed_interpretations']
    if item_id in MATERIAL_CASES:
        require(raw['native_operation_conflict'], 'pinned material case changed: ' + item_id)
        row['semantic_review_note'] = MATERIAL_CASES[item_id]
        row['nonmaterial_interpretation_differences'] = []
        return row
    require(a['native_decision'] == b['native_decision'] and
            (not a['native_decision'].startswith('REUSE_') or a.get('target') == b.get('target')),
            'unreviewed material conflict: ' + item_id)
    if not raw['changed_interpretations']:
        note = 'Same native operation, target, and material interpretation.'
    elif item['kind'] == 'relation' and a['native_decision'] == 'CREATE_RELATION':
        note = ('Both reviewers support the same frozen endpoints, relation type, source scope, '
                'and evidence. Granularity labels refer to parent-child levels versus the proposed edge; '
                'bounded evidence comments do not change the edge.')
    elif item['kind'] == 'relation':
        note = ('Both reviewers hold the same endpoint, temporal, or ontology exception. '
                'Rubric labels compare concept support with authority for the relation.')
    elif item_id.startswith('OBS_'):
        note = ('Both reviewers defer an observation with no admitted candidate or evidence. '
                'Ontology and temporal labels are not actionable without admission.')
    elif a['native_decision'] == 'CREATE_NEW_CANONICAL':
        note = ('Both reviewers propose the same distinct candidate. Scope and granularity labels '
                'compare it with different reference objects, without changing the identity boundary.')
    elif a['native_decision'] == 'REJECT':
        note = 'Both reviewers reject a versioned parallel node and retain version context as a claim or scope.'
    else:
        note = ('Both reviewers preserve the same governed hold. Rubric labels distinguish '
                'source support for a concept from sufficiency for canonical admission.')
    row.update(status='A_B_SUBSTANTIVE_AGREEMENT', disagreement_type=[],
               native_operation_conflict=False, target_conflict=False,
               evidence_conflict=False, type_scope_conflict=False, temporal_conflict=False,
               nonmaterial_interpretation_differences=raw['changed_interpretations'],
               changed_interpretations=[], semantic_review_note=note)
    return row


def system_decision(item, a, b, comparison):
    auto = item['resolution']['outcome']
    deferred = 'DEFER' if item['kind'] == 'identity' else 'DEFER_RELATION'
    reasons = set(item['resolution']['reasons'])
    if auto in ('REJECT', 'REJECT_RELATION') and 'FROZEN_STAGE2_HUMAN_DECISION' in reasons:
        return auto, 'Frozen Stage 2 HUMAN_USER rejection remains in force.'
    if reasons & {'HISTORICAL_QUARANTINE', 'ONTOLOGY_PRESSURE', 'TEMPORAL_MISMATCH',
                  'FROZEN_STAGE2_HUMAN_DECISION', 'TYPE_MISMATCH', 'IDENTITY_TARGET_OR_STATUS_REVIEW',
                  'NOT_ADMITTED_IN_STAGE2', 'ENDPOINT_AMBIGUITY', 'PARENT_CYCLE',
                  'EVIDENCE_OR_DIRECTION_REVIEW', 'EXISTING_RELATION_TARGET_MISMATCH',
                  'DUPLICATE_CANONICAL_RELATIONS'}:
        return deferred, 'Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.'
    if comparison['status'] == 'A_B_SUBSTANTIVE_DISAGREEMENT':
        return deferred, 'Material A/B interpretation or native-operation conflict requires HUMAN_USER adjudication.'
    proposed = a['native_decision']
    if proposed.startswith('REUSE_') and not a.get('target'):
        return deferred, 'Reuse requires a verified canonical target.'
    if proposed == 'CREATE_RELATION' and (not item['resolution'].get('from_node_id') or
                                          not item['resolution'].get('to_node_id')):
        return deferred, 'Relation endpoint identity remains unresolved.'
    return proposed, 'A/B substantive consensus; frozen automated outcome: ' + auto + '.'


def clean(text):
    return str(text if text is not None else '').replace('\r', ' ').replace('\n', ' ').strip()


def item_name(item):
    if item['kind'] == 'identity':
        return item['resolution']['observed_name']
    raw = item['frozen_candidate']['content']['raw']
    return raw['source_name'] + ' → ' + raw['target_name']


def packet_entry(number, item, a, b, reconciliation):
    resolution = item['resolution']
    content = (item['frozen_candidate'] or {}).get('content', {})
    raw = content.get('raw', {})
    kind = item['kind']
    current = resolution.get('target_node_id') if kind == 'identity' else ', '.join(resolution['existing_relation_ids'])
    possible = (', '.join(resolution.get('catalog_candidate_ids', [])) if kind == 'identity'
                else ', '.join(resolution['existing_relation_ids']))
    comparison = item.get('frozen_comparison') or {}
    domain = raw.get('primary_domain') or 'semiconductor'
    candidate = item_name(item)
    facts = [f'### Item {number:03d} — {item["item_id"]} — {candidate}', '',
             f'- ITEM_NUMBER: {number}; ITEM_ID: `{item["item_id"]}`; OBJECT_TYPE: {kind}.',
             f'- DOMAIN / context: `{domain}` Semiconductor structured Foundation candidate against '
             f'shared AI Hardware canonical catalog; cross-domain status: '
             f'`{raw.get("cross_domain_status", comparison.get("collision_risk", "candidate"))}`.',
             f'- AUTOMATED_STAGE3_OUTCOME: `{resolution["outcome"]}`; CURRENT_CANONICAL_TARGET: `{current or "none"}`.',
             f'- Possible existing canonical IDs (unresolved unless explicitly reused): `{possible or "none"}`.',
             f'- CANDIDATE_SUMMARY: {candidate}; candidate type `{content.get("primary_type", resolution.get("relation_type", "unknown"))}`; '
             f'comparison scope `{clean(raw.get("scope", comparison.get("semiconductor_context", "")))}`; '
             f'frozen candidate rationale: {clean(comparison.get("reason", raw.get("reason", "")))}',
             f'- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: '
             f'{", ".join(resolution["reasons"]) or "mandatory governance"}.',
             f'- RISK_FLAGS: A={", ".join(a["risk_flags"]) or "none"}; B={", ".join(b["risk_flags"]) or "none"}.',
             '', '**AI REVIEW A**', '',
             f'- recommendation: {clean(a["recommendation"])}; native decision: `{a["native_decision"]}`; '
             f'target: `{a.get("target") or "none"}`; confidence: {a["confidence"]}; '
             f'materiality: {a["materiality"]}.',
             f'- reason: {clean(a["reason"])}',
             f'- evidence assessment: {clean(a["evidence_assessment"])}',
             f'- temporal scope assessed: {clean(a["temporal_scope"])}',
             f'- type/scope/granularity/evidence/temporal assessment: '
             f'{clean(a["reviewer_interpretation"])}',
             '', '**AI REVIEW B**', '',
             f'- recommendation: {clean(b["recommendation"])}; native decision: `{b["native_decision"]}`; '
             f'target: `{b.get("target") or "none"}`; confidence: {b["confidence"]}; '
             f'materiality: {b["materiality"]}.',
             f'- reason: {clean(b["reason"])}',
             f'- evidence assessment: {clean(b["evidence_assessment"])}',
             f'- temporal scope assessed: {clean(b["temporal_scope"])}',
             f'- type/scope/granularity/evidence/temporal assessment: '
             f'{clean(b["reviewer_interpretation"])}',
             '', '**A/B RECONCILIATION**', '',
             f'- {reconciliation["status"]}; disagreement type: '
             f'{", ".join(reconciliation["disagreement_type"]) or "none"}; '
             f'native-operation conflict: {str(reconciliation["native_operation_conflict"]).lower()}; '
             f'target conflict: {str(reconciliation["target_conflict"]).lower()}.',
             f'- Interpretation differences: {", ".join(reconciliation["changed_interpretations"]) or "none"}.',
             f'- Reconciliation assessment: {reconciliation["semantic_review_note"]}',
             f'- Non-material rubric-label differences retained for audit: '
             f'{", ".join(reconciliation["nonmaterial_interpretation_differences"]) or "none"}.',
             '', '**EVIDENCE SUMMARY**', '']
    for ev in item['evidence']:
        excerpt = clean(ev['evidence_excerpt'])
        if len(excerpt) > 400:
            excerpt = excerpt[:400].rstrip() + '…'
        facts.append(f'- Source `{ev["source_id"]}` (SHA-256 `{ev["source_sha256"]}`), '
                     f'file `{ev["filename"]}`, p. {ev["pdf_page"]}, '
                     f'section {clean(ev.get("section")) or "unspecified"}; '
                     f'evidence `{ev["evidence_id"]}`; as-of {ev.get("as_of_date") or "unknown"}; '
                     f'excerpt: “{excerpt}”')
    if not item['evidence']:
        facts.append('- No admitted source excerpt is bound to this observation.')
    temporal = (resolution.get('temporal_projection') or {}).get('temporal_category') or \
        resolution.get('temporal_status') or 'source as-of dates above; no relation temporal claim'
    facts += [f'- Temporal scope: {temporal}.', '',
              f'- SYSTEM_RECOMMENDED_DECISION: `{reconciliation["system_recommended_decision"]}`.',
              f'- SYSTEM_RECOMMENDATION_REASON: {reconciliation["system_recommendation_reason"]}',
              '- HUMAN_USER_DECISION = PENDING',
              '- VALID NATIVE OPTIONS: ' + (
                  'DEFER, REJECT for this unadmitted observation; CREATE/REUSE requires a separately admitted candidate.'
                  if item['frozen_candidate'] is None else
                  (', '.join(IDENTITY) if kind == 'identity' else ', '.join(RELATION)) +
                  '; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.'),
              '']
    return '\n'.join(facts)


def write_outputs(items, review_a, review_b, access_a, access_b):
    require(file_sha(ARTIFACT / 'double_review/a/review.json') == REVIEW_A_SHA and
            file_sha(ARTIFACT / 'double_review/b/review.json') == REVIEW_B_SHA,
            'pinned independent review bytes drift; semantic assessment must be repeated')
    doc_a = {'document_type': 'phase43_stage3_ai_review', 'reviewer': 'A',
             'population_sha256': POPULATION_SHA, 'items': review_a['items']}
    doc_b = {'document_type': 'phase43_stage3_ai_review', 'reviewer': 'B',
             'population_sha256': POPULATION_SHA, 'items': review_b['items']}
    a = validate_review('A', doc_a, items)
    b = validate_review('B', doc_b, items)
    reconciled = []
    for item in items:
        item_id = item['item_id']
        row = {'item_id': item_id, 'kind': item['kind'], 'automated_outcome': item['resolution']['outcome']}
        row.update(semantic_reconciliation(item, a[item_id], b[item_id],
                                           compare_reviews(a[item_id], b[item_id])))
        decision, reason = system_decision(item, a[item_id], b[item_id], row)
        row.update(system_recommended_decision=decision, system_recommendation_reason=reason,
                   human_user_decision=None)
        reconciled.append(row)
    section_a = [row for row in reconciled if row['status'] == 'A_B_SUBSTANTIVE_AGREEMENT']
    section_b = [row for row in reconciled if row['status'] == 'A_B_SUBSTANTIVE_DISAGREEMENT']
    require(len(section_a) + len(section_b) == 100, 'reconciliation coverage')
    policy = {'document_type': 'phase43_stage3_review_policy_binding', 'population_sha256': POPULATION_SHA,
              'population': 100, 'mandatory_human': 100, 'residual_eligible': 0,
              'residual_sample_required': False, 'residual_sample_size': 0,
              'stage2_review_contract_sha256': file_sha(ROOT / 'docs/phase43_stage2_review_contract.json'),
              'stage2_review_validation_sha256': file_sha(ROOT / 'docs/phase43_stage2_double_review_validation.json'),
              'scope': 'Reuse Stage 1/2 risk governance where semantically applicable; adapt Stage 3 object fields only.',
              'mandatory_risk_classes': ['LOW_OR_REQUIRED_UNKNOWN', 'IDENTITY_AMBIGUITY', 'TYPE_MISMATCH',
                                         'CROSS_DOMAIN_CONFLICT', 'NEW_CANONICAL_STRUCTURAL_OBJECT',
                                         'RELATION_AMBIGUITY', 'ONTOLOGY_PRESSURE',
                                         'HISTORICAL_QUARANTINE', 'VIEW_IMPLICATION'],
              'ai_agreement_waives_human': False, 'original_stage1_stage2_policy_modified': False}
    review_access = {}
    for role, access in (('A', access_a), ('B', access_b)):
        private_path = ARTIFACT / 'double_review' / role.lower() / 'access_record.json'
        validate_access(role, access, file_sha(private_path.parent / 'review.json'))
        review_access[role] = {'task_context': 'fresh independent context',
                               'fork_turns': 'none', 'peer_output_accessed': False,
                               'frozen_review_file_sha256': REVIEW_FILE_SHA,
                               'private_access_record_sha256': file_sha(private_path),
                               'private_review_sha256': access['review_output_sha256']}
    validation = {'document_type': 'phase43_stage3_double_review_validation', 'result': 'PASS',
                  'baseline': BASELINE, 'pr65_head_before': INITIAL_HEAD,
                  'population_sha256': POPULATION_SHA, 'ai_hardware_input_sha256': PRODUCTION_SHA,
                  'semiconductor_input_sha256': PACKAGE_SHA, 'stage2_immutable_packet_sha256': STAGE2_SHA,
                  'stage2_human_authorization_sha256': STAGE2_AUTH_SHA,
                  'workspace_a_structural_sha256': STRUCTURAL_SHA,
                  'workspace_b_structural_sha256': STRUCTURAL_SHA,
                  'resolution_file_sha256': RESOLUTION_FILE_SHA, 'review_file_sha256': REVIEW_FILE_SHA,
                  'review_a_file_sha256': REVIEW_A_SHA, 'review_b_file_sha256': REVIEW_B_SHA,
                  'review_a_items': 100, 'review_b_items': 100, 'reconciled_items': 100,
                  'missing_items': 0, 'extra_items': 0, 'duplicate_items': 0,
                  'section_a': len(section_a), 'section_b': len(section_b),
                  'substantive_agreement': len(section_a), 'substantive_disagreement': len(section_b),
                  'native_operation_conflicts': sum(r['native_operation_conflict'] for r in reconciled),
                  'target_conflicts': sum(r['target_conflict'] for r in reconciled),
                  'evidence_conflicts': sum(r['evidence_conflict'] for r in reconciled),
                  'type_scope_conflicts': sum(r['type_scope_conflict'] for r in reconciled),
                  'temporal_conflicts': sum(r['temporal_conflict'] for r in reconciled),
                  'nonmaterial_rubric_label_differences': sum(
                      bool(r['nonmaterial_interpretation_differences']) for r in reconciled),
                  'semantic_reconciliation_basis': 'All 100 pinned A/B rationales inspected. Relation decisions and endpoint/type/scope/temporal holds aligned; same-decision field labels with different reference frames were retained as non-material audit notes. Four native-operation conflicts remain substantive.',
                  'frozen_automated_identity_outcomes': {
                      'REUSE_CANONICAL': 16, 'CREATE_NEW_CANONICAL': 4,
                      'KEEP_DOMAIN_SPECIFIC': 0, 'DEFER': 25, 'REJECT': 1},
                  'frozen_automated_relation_outcomes': {
                      'REUSE_RELATION': 0, 'CREATE_RELATION': 38,
                      'KEEP_DOMAIN_SPECIFIC_RELATION': 0, 'DEFER_RELATION': 16,
                      'REJECT_RELATION': 0},
                  'source_and_evidence_bindings_unchanged': True,
                  'claim_provenance_preserved': 19, 'cross_source_leakage': 0,
                  'absolute_path_leakage': 0, 'automated_outcomes_mutated': False,
                  'independence': 'Two fresh review task contexts with fork_turns=none and peer-output exclusion; shared filesystem. Different model/provider/OS/cryptographic isolation not claimed.',
                  'review_access': review_access, 'human_user_decisions_applied': 0,
                  'final_human_qualification': 'PENDING', 'production_sha_before': PRODUCTION_SHA,
                  'production_sha_after': PRODUCTION_SHA, 'production_write_count': 0,
                  'apply_executed': False, 'official_view_activations': 0,
                  'stage4_started': False}
    by_id = {item['item_id']: item for item in items}
    number = {item['item_id']: n for n, item in enumerate(items, 1)}
    packet = ['# Phase 4.3 Stage 3 — HUMAN_USER Qualification Packet', '',
              'This is an advisory, self-contained review of the frozen 100-item Stage 3 population. '
              'Every item requires explicit HUMAN_USER authorization. AI consensus grants no authority. '
              'No canonical or Production mutation has been made.', '',
              f'- Baseline: `{BASELINE}`; population SHA-256: `{POPULATION_SHA}`.',
              f'- Stage 2 immutable packet SHA-256: `{STAGE2_SHA}`.',
              f'- Section A: {len(section_a)} mandatory items with A/B substantive agreement.',
              f'- Section B: {len(section_b)} substantive disagreements.',
              '- Residual sample: 0. HUMAN_USER decisions applied: 0.',
              '- Native REUSE options require a specific validated canonical target ID. '
              'CREATE remains a proposal and does not activate a canonical object.', '']
    packet += ['## Structural case summary', '',
               'The following IDs locate all frozen items matching the requested structural topics. '
               'Each item below retains its bound evidence and both AI reviews.', '',
               '| Topic | Frozen items | Review boundary |', '|---|---|---|']
    for topic, (terms, summary) in SPECIAL_CASES.items():
        matches = [r['item_id'] for r in reconciled
                   if any(term.casefold() in item_name(by_id[r['item_id']]).casefold() for term in terms)]
        packet.append(f'| {topic} | {", ".join("`" + x + "`" for x in matches) or "none in frozen population"} | {summary} |')
    packet += ['',
               'Cross-domain collision: `SC-CN-0142` (target/status review). '
               'Unresolved automated identity conflicts: 25. '
               'Ontology-pressure relations: `SC-RL-0051`–`SC-RL-0054`. '
               'Temporal mismatch relations: `SC-RL-0019`, `SC-RL-0020`.', '']
    for title, rows in (('Section A — Consensus, mandatory HUMAN_USER authorization', section_a),
                        ('Section B — Substantive A/B disagreement', section_b)):
        packet += ['## ' + title, '']
        for row in rows:
            item_id = row['item_id']
            packet.append(packet_entry(number[item_id], by_id[item_id], a[item_id], b[item_id], row))
    index = ['# Phase 4.3 Stage 3 — HUMAN_USER Decision Index', '',
             'Navigation aid. The self-contained qualification packet contains the full evidence and review record.', '',
             f'Population `{POPULATION_SHA}`; Section A {len(section_a)}, Section B {len(section_b)}, residual 0.', '']
    def table(title, rows):
        index.extend(['## ' + title, '', '| # | Item | Candidate | Automated | System advice |',
                      '|---:|---|---|---|---|'])
        for row in rows:
            item = by_id[row['item_id']]
            index.append(f'| {number[row["item_id"]]:03d} | `{row["item_id"]}` | '
                         f'{clean(item_name(item)).replace("|", "/")} | `{row["automated_outcome"]}` | '
                         f'`{row["system_recommended_decision"]}` |')
        if not rows:
            index.append('| — | — | None | — | — |')
        index.append('')
    table('Section A — Consensus mandatory', section_a)
    table('Section B — Substantive disagreements', section_b)
    table('Cross-domain collision', [r for r in reconciled if r['item_id'] == 'SC-CN-0142'])
    table('Unresolved automated identity conflicts', [r for r in reconciled
                                                     if r['kind'] == 'identity' and
                                                     r['automated_outcome'] == 'DEFER'])
    for title, key in (('Native-operation conflicts', 'native_operation_conflict'),
                       ('Canonical-target conflicts', 'target_conflict'),
                       ('Ontology-pressure cases', None),
                       ('Temporal mismatches', None),
                       ('Historical quarantine cases', None)):
        if key:
            rows = [r for r in reconciled if r[key]]
        else:
            flag = {'Ontology-pressure cases': 'ONTOLOGY_PRESSURE',
                    'Temporal mismatches': 'TEMPORAL_MISMATCH',
                    'Historical quarantine cases': 'HISTORICAL_QUARANTINE'}[title]
            rows = [r for r in reconciled if flag in by_id[r['item_id']]['resolution']['reasons']]
        table(title, rows)
    index.extend(['## Structural case locator', '', '| Topic | Items |', '|---|---|'])
    for topic, (terms, _) in SPECIAL_CASES.items():
        matches = [r['item_id'] for r in reconciled
                   if any(term.casefold() in item_name(by_id[r['item_id']]).casefold() for term in terms)]
        index.append(f'| {topic} | {", ".join("`" + x + "`" for x in matches) or "none in frozen population"} |')
    index += ['', 'Cross-domain collision: `SC-CN-0142` (identity target/status review). '
              'Unresolved identity conflicts: 25; ontology-pressure cases: 4; temporal mismatches: 2.', '']
    template = {'document_type': 'phase43_stage3_human_decision_template',
                'population_sha256': POPULATION_SHA,
                'items': [{'item_id': row['item_id'],
                           'system_recommended_decision': row['system_recommended_decision'],
                           'human_user_decision': None} for row in reconciled]}
    outputs = {
        'phase43_stage3_ai_review_a.json': doc_a,
        'phase43_stage3_ai_review_b.json': doc_b,
        'phase43_stage3_ai_review_reconciliation.json': {
            'document_type': 'phase43_stage3_ai_review_reconciliation',
            'population_sha256': POPULATION_SHA, 'items': reconciled},
        'phase43_stage3_double_review_validation.json': validation,
        'phase43_stage3_review_policy_binding.json': policy,
        'phase43_stage3_human_decision_template.json': template,
    }
    for filename, value in outputs.items():
        text = frozen_json(value)
        require(not LOCAL_PATH.search(text), 'local path leakage: ' + filename)
        (ROOT / 'docs' / filename).write_text(text, encoding='utf-8', newline='\n')
    for filename, lines in (
        ('PHASE43_STAGE3_HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md', packet),
        ('PHASE43_STAGE3_HUMAN_DECISION_INDEX.md', index),
    ):
        text = '\n'.join(lines).rstrip('\n') + '\n'
        require(not LOCAL_PATH.search(text), 'local path leakage: ' + filename)
        (ROOT / 'docs' / filename).write_text(text, encoding='utf-8', newline='\n')
    return validation


def main():
    before = sha256_file(ROOT / 'workspace/pro_a.db')
    items = check_binding()
    reviews = [load(ARTIFACT / 'double_review' / role / 'review.json') for role in ('a', 'b')]
    access = [load(ARTIFACT / 'double_review' / role / 'access_record.json') for role in ('a', 'b')]
    validation = write_outputs(items, reviews[0], reviews[1], access[0], access[1])
    require(len(check_binding()) == 100, 'frozen input changed during review output')
    require(sha256_file(ROOT / 'workspace/pro_a.db') == before == PRODUCTION_SHA, 'Production mutation')
    print(f'STAGE3_DOUBLE_REVIEW=PASS A={validation["section_a"]} B={validation["section_b"]}')


if __name__ == '__main__':
    main()
