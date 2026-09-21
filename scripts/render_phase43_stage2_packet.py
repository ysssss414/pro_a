"""Render sanitized audit artifacts and a local human packet from sealed reviews."""
import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import re
from reconcile_phase43_stage2 import digest, file_sha, load, write_once, read_wip


def public(value):
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items()}
    if isinstance(value, list):
        return [public(v) for v in value]
    if isinstance(value, str):
        # Preserve logical identifiers; do not publish absolute workstation paths.
        return re.sub(r'[A-Za-z]:[\\/][^\n"<>]*', '[PRIVATE_LOCAL_PATH]', value)
    return value


def main(root):
    frozen = root / 'frozen'
    packet = load(frozen / 'foundation_packet.json')
    manifest = load(frozen / 'population_manifest.json')
    contract = load(root / 'review_contract.json')
    reviews = {role: load(root / f'review_{role}/review.json') for role in ['A', 'B']}
    by_review = {role: {r['candidate_id']: r for r in data['records']} for role, data in reviews.items()}
    reconciliation = load(root / 'reconciliation.json')
    sample = load(root / 'residual_sample.json')
    native = {row['candidate_id']: (kind, row) for kind, rows in packet['objects'].items() for row in rows}
    evidence = {row['evidence_id']: row for row in (json.loads(line) for line in
                (frozen / 'package/evidence_registry.jsonl').read_text('utf-8').splitlines() if line.strip())}
    sources = {r['raw']['physical_source_id']: r for r in packet['registry']['sources']}
    canonical = {r['node_id']: r for r in load(frozen / 'canonical_catalog.json')['nodes']}
    source_bindings = []
    human_items = []
    selected = set(sample['selected_ids'])
    for rec in reconciliation:
        key = rec['candidate_id']
        kind, obj = native[key]
        content = obj['content']
        raw = content.get('raw', {})
        a, b = by_review['A'][key], by_review['B'][key]
        ids = next(r['evidence_identity'] for r in manifest['items'] if r['candidate_id'] == key)
        ids = sorted(set(ids) | set(a['evidence_refs']) | set(b['evidence_refs']))
        missing = set(ids) - set(evidence)
        if missing:
            raise ValueError(f'UNKNOWN_EVIDENCE_REFERENCE: {key} {missing}')
        proof = [evidence[x] for x in ids]
        source_ids = sorted({e['physical_source_id'] for e in proof})
        source_bindings.append({'candidate_id': key, 'source_identities': [
            {'physical_source_id': sid, 'canonical_source_id': sources[sid]['resolved_source_id'],
             'source_sha256': sources[sid]['expected_sha256']} for sid in source_ids], 'evidence_ids': ids})
        if not rec['mandatory_human'] and key not in selected:
            continue
        if rec['comparison'] == 'A_B_DISAGREEMENT':
            section = 'B'
        elif rec['mandatory_human']:
            section = 'A'
        else:
            section = 'C'
        title = content.get('canonical_name') or content.get('statement') or content.get('alias') or raw.get('summary') or raw.get('native_proposition') or key
        targets = sorted({v for r in [a, b] for k, v in r['proposed_operation'].items()
                          if k in {'target_id', 'from_ref', 'to_ref'} and v})
        target_names = {t: canonical[t]['canonical_name'] if t in canonical else
                        native[t][1]['content'].get('canonical_name', t) if t in native else t for t in targets}
        summary_fields = {
            'nodes': {'名称': content.get('canonical_name'), 'Node 类型': content.get('primary_type'),
                      '已有身份': content.get('resolved_node_id'), '备选身份': raw.get('possible_existing_node_id'),
                      '边界说明': raw.get('granularity_reason')},
            'aliases': {'别名': content.get('alias'), '提议所有者名称': raw.get('canonical_name'),
                        '提议所有者': raw.get('target_existing_node_id') or raw.get('target_candidate_id'),
                        '已占用所有者': raw.get('existing_alias_owners')},
            'claims': {'命题': content.get('statement') or raw.get('statement'), '主体': raw.get('subject_name'),
                       '主体 ID': content.get('subject_ref') or raw.get('subject_ref'), '性质': content.get('nature'),
                       '事实时间': raw.get('fact_time'), '来源时点': raw.get('source_as_of'),
                       '时间类别': content.get('temporal_category'), '范围': raw.get('scope')},
            'relations': {'命题': raw.get('native_proposition'), '起点': raw.get('source_name'),
                          '终点': raw.get('target_name'), '关系类型': content.get('relation_type'),
                          '范围': content.get('scope'), '时间类别': content.get('temporal_status')},
            'baseline_views': {'概述': raw.get('summary'), '节点': raw.get('node_ref'),
                               '核心结论': [r['statement'] for r in raw.get('core_structure', [])],
                               '不确定性': raw.get('uncertainties'), '状态': raw.get('state')},
        }[kind]
        human_items.append({'candidate_id': key, 'candidate_type': kind, 'section': section,
            'label': title, 'candidate_summary': summary_fields, 'current_operation': content['classification'],
            'current_canonical_target': content.get('resolved_node_id') or content.get('target_ref'),
            'ai_review_a': a, 'ai_review_b': b, 'comparison': rec['comparison'],
            'mandatory_triggers': rec['mandatory_triggers'], 'initial_reasons': content.get('reasons', []),
            'target_names': target_names, 'source_metadata': [{'physical_source_id': sid,
                'canonical_source_id': sources[sid]['resolved_source_id'], 'title': sources[sid]['raw'].get('title'),
                'publisher': sources[sid]['raw'].get('publisher'), 'sha256': sources[sid]['expected_sha256']} for sid in source_ids],
            'evidence': proof, 'allowed_decisions': obj['allowed_decisions'],
            'human_input': {'decision': '', 'reason': '', 'target_id': ''}})
    human_items.sort(key=lambda r: (r['section'], r['candidate_id']))
    mandatory = [r for r in reconciliation if r['mandatory_human']]
    status_counts = Counter(r['comparison'] for r in reconciliation)
    report = {'document_type': 'phase43_stage2_ai_double_review_results', 'result': 'PASS',
        'entry_implementation_head': manifest['entry_implementation_head'], 'total_reviewed': len(reconciliation),
        'human_required_input': 234, 'population_sha256': manifest['ordered_population_sha256'],
        'exact_agreement': status_counts['A_B_EXACT_AGREEMENT'],
        'substantive_agreement': status_counts['A_B_SUBSTANTIVE_AGREEMENT'],
        'disagreement': status_counts['A_B_DISAGREEMENT'],
        'agreement_rate': (len(reconciliation) - status_counts['A_B_DISAGREEMENT']) / len(reconciliation),
        'mandatory_unique': len(mandatory), 'trigger_counts': dict(sorted(Counter(t for r in mandatory for t in r['mandatory_triggers']).items())),
        'residual_eligible': sample['eligible_count'], 'random_core': sample['core_size'],
        'coverage_supplements': len(sample['coverage_supplements']), 'sampled_items': len(sample['selected_ids']),
        'total_human_items': len(human_items), 'sections': dict(Counter(r['section'] for r in human_items)),
        'reviewer_results': {role: {'reviewed': len(data['records']),
            'recommendations': dict(Counter(r['recommendation'] for r in data['records'])),
            'sealed_review_sha256': file_sha(root / f'review_{role}/review.json')} for role, data in reviews.items()},
        'human_qualification': 'PENDING', 'capacity': 'CAPACITY_UNRESOLVED_NO_DAILY_BUDGET_ASSUMED',
        'wip_before': 274, 'wip_after': None, 'new_intake_allowed': False,
        'wip_state': 'HARD_STOP', 'production_sha_before': manifest['production_sha_before'],
        'production_sha_after': None, 'production_write_count': 0, 'apply_executed': False,
        'official_view_activation': False, 'human_decisions_applied': False, 'stage3_started': False,
        'pr64_merged': False, 'independence': 'Two actual fresh collaboration contexts; shared filesystem; no model diversity or OS isolation claim',
        'runtime_code_modified': False, 'gold_case_io_schema_conformance_claimed': False,
        'stage2_adapter': contract['version'], 'scope_authorization_sha256': contract['scope_authorization_sha256']}
    for path, expected in load(root / 'protected_inputs_before.json').items():
        if file_sha(path) != expected:
            raise ValueError('PROTECTED_INPUT_MUTATED')
        if Path(path).name == 'workbench.sqlite3':
            report['wip_after'] = read_wip(path)
        if Path(path).name == 'pro_a.db' and 'q2' not in Path(path).parts:
            report['production_sha_after'] = file_sha(path)
    if report['wip_after'] != 274 or report['production_sha_after'] != report['production_sha_before']:
        raise ValueError('PRODUCTION_WIP_BOUNDARY')
    hp = {'document_type': 'stage2_bounded_human_qualification_packet', 'population_sha256': manifest['ordered_population_sha256'],
          'reconciliation_sha256': file_sha(root / 'reconciliation.json'), 'sample_sha256': file_sha(root / 'residual_sample.json'),
          'human_completion': {'reviewer': '', 'reason': ''}, 'human_decisions_applied': False,
          'mutation_authority_granted': False, 'page_size': 20, 'items': human_items}
    write_once(root / 'human_qualification_packet.private.json', hp)
    out = root / 'public'
    write_once(out / 'phase43_stage2_review_population_manifest.json', manifest)
    write_once(out / 'phase43_stage2_review_contract.json', contract | {'scope_authorization': load(root / 'scope_authorization.json'),
               'dispatch': load(root / 'dispatch_receipt.json'), 'scope_pending_marker_in_snapshot': 'SUPERSEDED_BY_EXPLICIT_SCOPE_AUTHORIZATION'})
    write_once(out / 'phase43_stage2_review_source_bindings.json', source_bindings)
    for role, data in reviews.items():
        write_once(out / f'phase43_stage2_ai_review_{role.lower()}.json', public(data) | {'private_sealed_original_sha256': file_sha(root / f'review_{role}/review.json')})
    write_once(out / 'phase43_stage2_ai_review_reconciliation.json', {'summary': report, 'items': reconciliation, 'residual_sample': sample})
    # Logical evidence pointers only in tracked artifact. Full excerpts remain local.
    sanitized_items = []
    for row in human_items:
        sanitized_items.append(public({k: v for k, v in row.items() if k != 'evidence'}) | {
            'evidence_pointers': [{k: e[k] for k in ['evidence_id', 'source_id', 'source_sha256', 'pdf_page', 'section', 'excerpt_sha256']} for e in row['evidence']]})
    write_once(out / 'phase43_stage2_human_qualification_packet.json', {**hp, 'items': sanitized_items})
    write_once(root / 'result_summary.json', report)
    render_html(root, hp, report)
    render_markdown(root, hp, report)
    print(json.dumps(report, ensure_ascii=False))


def render_markdown(root, packet, report):
    pages = root / 'human_pages'
    pages.mkdir(exist_ok=True)
    index = ['# Stage 2 人工资格审核包', '',
             f"必审 {report['mandatory_unique']} 项（含分歧 {report['disagreement']}）；抽样 {report['sampled_items']} 项；合计 {report['total_human_items']} 项。", '',
             '每页最多 20 项；人工选择尚未填写。本文件不授予正式写入或 View 激活权限。', '',
             'A：共识下的必审项；B：实质分歧；C：随机样本与覆盖补充。', '']
    for offset in range(0, len(packet['items']), 20):
        filename = f'page_{offset // 20 + 1:02}.md'
        index.append(f'- [第 {offset // 20 + 1} 页]({(pages / filename).as_posix()})')
        lines = [f'# Stage 2 审核 · 第 {offset // 20 + 1} 页', '']
        for row in packet['items'][offset:offset + 20]:
            lines.extend([f"## {row['section']} · {row['candidate_id']} · {row['label']}", '',
                          f"类型：{row['candidate_type']}；当前提议：{row['current_operation']}；对账：{row['comparison']}", '',
                          '必审触发：' + (', '.join(row['mandatory_triggers']) or '无；抽样复核'), ''])
            for key, value in row['candidate_summary'].items():
                if value:
                    lines.extend([f"**{key}**：{value if not isinstance(value, list) else '；'.join(value)}", ''])
            for side in ['a', 'b']:
                ai = row['ai_review_' + side]
                lines.extend([f"**AI {side.upper()}**：{ai['recommendation']} / {ai['native_decision']}；{ai['concise_rationale']}", '',
                              '建议操作：`' + json.dumps(ai['proposed_operation'], ensure_ascii=False) + '`', ''])
            lines.extend(['目标名称：' + json.dumps(row['target_names'], ensure_ascii=False), ''])
            for source in row['source_metadata']:
                lines.extend([f"来源：{source['title']} · {source['physical_source_id']}", ''])
            for proof in row['evidence']:
                lines.extend([f"证据：{proof['evidence_id']} · PDF p.{proof['pdf_page']} · {proof['section']}", '',
                              '> ' + proof['evidence_excerpt'].replace('\n', '\n> '), ''])
            lines.extend(['**人工选项**：' + ' / '.join(row['allowed_decisions']), '',
                          '人工决定：________　目标 ID（如适用）：________', '', '---', ''])
        (pages / filename).write_text('\n'.join(lines), encoding='utf-8')
    (root / 'HUMAN_QUALIFICATION_PACKET.md').write_text('\n'.join(index) + '\n', encoding='utf-8')


def render_html(root, packet, report):
    data = json.dumps(packet, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stage 2 人工资格审核包</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;background:#f5f6f8;color:#172333;font:16px/1.6 system-ui}header,.card{background:white;padding:24px;margin:18px 0;border:1px solid #d9dfe5;border-radius:10px}h1{font-size:26px}h2{font-size:19px}small,.muted{color:#536174}nav{position:sticky;top:0;background:#f5f6f8;padding:12px 0;z-index:1}button,select,input{font:inherit;padding:7px;margin:4px;max-width:90%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 monospace}blockquote{margin:8px 0;padding:12px;border-left:3px solid #607c99;background:#f4f7fa}label{display:block}summary{cursor:pointer}strong{color:#243e61}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<header><h1>Stage 2 · 人工资格审核包</h1><p id="counts"></p><p>每页最多 20 项。A 为共识下仍须人工判断的风险项，B 为双审实质分歧，C 为非必审总体的随机样本与覆盖补充。三节不重复计数。</p><p>所有人工字段初始为空。AI 结论只是建议；本页面不会提交、应用、激活 View 或修改 Production。正式 Node CREATE / View 写入仍需单独满足人类授权流程。</p><details><summary>审核口径与抽样边界</summary><p>沿用已授权 V2 的 14 风险与必要 UNKNOWN 必审规则。抽样使用 Regime B：10% 错误检测情景、95% 发现目标、核心至少 20 项（总体不足则全查）。发现任何实质错误即停止资格通过并按冻结政策扩审；零发现不代表零错误。此处只准备样本，未取得人审结果。</p><p>双审使用两个独立上下文，未声称不同模型或操作系统隔离。保持原有 274 WIP 与新 intake HARD_STOP。</p></details></header>
<nav><select id="section" onchange="page=0;render()"><option value="">全部</option><option value="A">A · Mandatory exceptions</option><option value="B">B · A/B disagreements</option><option value="C">C · Residual sample</option></select><button onclick="page=Math.max(0,page-1);render()">上一页</button><span id="page"></span><button onclick="page++;render()">下一页</button><button onclick="download()">下载未应用的审核记录</button></nav><main id="cards"></main>
<script id="packet" type="application/json">__DATA__</script><script>
const packet=JSON.parse(document.getElementById('packet').textContent),answers={};let page=0;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty=x=>esc(JSON.stringify(x,null,2));
document.getElementById('counts').textContent='__COUNTS__';
function setAnswer(id,key,value){answers[id]??={decision:'',reason:'',target_id:''};answers[id][key]=value;}
function render(){const section=document.getElementById('section').value,rows=packet.items.filter(r=>!section||r.section===section);page=Math.min(page,Math.max(0,Math.ceil(rows.length/20)-1));document.getElementById('page').textContent=`${page+1} / ${Math.max(1,Math.ceil(rows.length/20))} 页 · ${rows.length} 项`;
document.getElementById('cards').innerHTML=rows.slice(page*20,page*20+20).map(r=>{const answer=answers[r.candidate_id]||r.human_input;return `<article class="card"><small>${esc(r.section+' · '+r.candidate_type+' · '+r.candidate_id)}</small><h2>${esc(r.label)}</h2><p><strong>当前状态：</strong>${esc(r.current_operation)}　<strong>对账：</strong>${esc(r.comparison)}</p><dl>${Object.entries(r.candidate_summary).filter(([k,v])=>v!==null&&v!=='').map(([k,v])=>`<dt><strong>${esc(k)}</strong></dt><dd>${esc(Array.isArray(v)?v.join('；'):v)}</dd>`).join('')}</dl><p><strong>必审触发：</strong>${esc(r.mandatory_triggers.join(', ')||'随机样本；无必审触发')}</p><div class="grid">${['a','b'].map(side=>{const a=r['ai_review_'+side];return `<div><strong>AI ${side.toUpperCase()} · ${esc(a.recommendation)} / ${esc(a.native_decision)}</strong><p>${esc(a.concise_rationale)}</p><small>Confidence: ${esc(a.overall_confidence)} · Evidence: ${esc(a.evidence_sufficiency)}</small><pre>${pretty(a.proposed_operation)}</pre></div>`}).join('')}</div><p><strong>目标名称：</strong>${esc(Object.entries(r.target_names).map(([id,n])=>id+' = '+n).join('；')||'不适用')}</p><details><summary>来源与证据（${r.evidence.length} 条）</summary>${r.source_metadata.map(s=>`<p>${esc(s.title)}<br><small>${esc(s.publisher+' · '+s.physical_source_id+' / '+s.canonical_source_id)}</small></p>`).join('')}${r.evidence.map(e=>`<p><small>${esc(e.evidence_id+' · PDF p.'+e.pdf_page+' · '+e.section)}</small></p><blockquote>${esc(e.evidence_excerpt)}</blockquote>`).join('')}</details><details><summary>风险详情与初始标记</summary><p>${esc(r.initial_reasons.join(', '))}</p><div class="grid">${['a','b'].map(s=>`<pre>${pretty(r['ai_review_'+s].risk_flags)}\n${pretty(r['ai_review_'+s].risk_reasons)}</pre>`).join('')}</div></details><label>人工选择（原生词汇；留空表示未审）<select onchange="setAnswer('${r.candidate_id}','decision',this.value)"><option value="">尚未决定</option>${r.allowed_decisions.map(x=>`<option ${answer.decision===x?'selected':''}>${esc(x)}</option>`).join('')}</select></label><label>目标 ID（REUSE / ATTACH 或更换目标时填写）<input value="${esc(answer.target_id)}" onchange="setAnswer('${r.candidate_id}','target_id',this.value)"></label><details><summary>可选补充说明（只有决策需要时填写）</summary><input value="${esc(answer.reason)}" onchange="setAnswer('${r.candidate_id}','reason',this.value)"></details></article>`}).join('');}
function download(){const output={document_type:'stage2_human_review_draft_unapplied',population_sha256:packet.population_sha256,reconciliation_sha256:packet.reconciliation_sha256,human_completion:{reviewer:'',reason:''},human_decisions_applied:false,items:packet.items.map(r=>({candidate_id:r.candidate_id,human_input:answers[r.candidate_id]||r.human_input}))};const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json'}));link.download='stage2_human_review_draft_unapplied.json';link.click();URL.revokeObjectURL(link.href);}
render();</script></html>'''
    counts = f"双审 {report['total_reviewed']} 项；必审 {report['mandatory_unique']} 项（含分歧 {report['disagreement']}）；抽样 {report['sampled_items']} 项；本包共 {report['total_human_items']} 项。"
    html = html.replace('__DATA__', data).replace('__COUNTS__', counts)
    path = root / 'HUMAN_QUALIFICATION_PACKET.html'
    encoded = html.encode('utf-8')
    if path.exists() and path.read_bytes() != encoded:
        raise ValueError('HTML_FROZEN_OUTPUT_CONFLICT')
    if not path.exists():
        path.write_bytes(encoded)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    main(parser.parse_args().root)
