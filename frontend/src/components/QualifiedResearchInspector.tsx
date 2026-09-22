import type { QualifiedIdentity } from "../api/research";

export function QualifiedResearchInspector({ data, onVisual }: {
  data: QualifiedIdentity; onVisual: (visualId: string) => void;
}) {
  return <article className="qualified-inspector">
    <span className="qualified-badge">QUALIFIED · {data.qualification_stage}</span>
    <h2>{data.display_name}</h2>
    <p>{data.primary_type} · {data.candidate_id}</p>
    <dl>
      <dt>Knowledge State</dt><dd>Qualified Identity</dd>
      <dt>Production Canonical</dt><dd>No</dd>
      <dt>Production Applied</dt><dd>No</dd>
      <dt>HUMAN_USER decision</dt><dd>{data.human_decision}</dd>
      <dt>Authorization basis</dt><dd>{data.authorization_basis}</dd>
      <dt>Human reason</dt><dd>{data.human_reason}</dd>
    </dl>
    <details className="qualified-provenance"><summary>Frozen qualification provenance</summary>
      <p>Phase 4.3 {data.qualification_stage} · HUMAN_USER · Production Applied: No</p>
      <p>Source population SHA256: {data.qualification_population_sha256}</p>
      <p>Candidate content SHA256: {data.candidate_content_sha256}</p>
      <p>Decision artifact SHA256: {data.qualification_decision_sha256}</p>
    </details>
    <section><h3>Qualification coverage</h3>
      <p>{data.evidence.length} bound evidence items · {data.relations.length} qualified relations</p>
      <p>No Official Current View — object is not in Production.</p>
    </section>
    <section><h3>Frozen qualification evidence</h3>
      {data.evidence.length ? <ul>{data.evidence.map((item) =>
        <li key={String(item.evidence_id)}><strong>{String(item.evidence_id)}</strong>
          {" · "}{String(item.source_title ?? item.source_id ?? "")}
          {" · "}{String(item.section ?? "")} · page {String(item.pdf_page ?? "unknown")}
          {Boolean(item.excerpt) && <p>{String(item.excerpt)}</p>}</li>)}</ul> :
        <p>No bounded evidence excerpt in this presentation slice.</p>}
    </section>
    <section><h3>Qualified relations</h3>
      {data.relations.length ? <ul>{data.relations.map((relation) =>
        <li key={String(relation.candidate_id)}>
          <strong>{String(relation.candidate_id)}</strong> · {String(relation.relation_type)} · Qualified, not canonical
          <div>From: {String(relation.from_visual_id)} · {String(relation.from_endpoint_authority)}</div>
          <div>To: {String(relation.to_visual_id)} · {String(relation.to_endpoint_authority)}</div>
          {[relation.from_visual_id, relation.to_visual_id].map((visual) => {
            const id = String(visual);
            if (id === data.visual_id) return null;
            return id.startsWith("endpoint-ref:") ? <span key={id}>Endpoint Reference: {id.slice(13)} · identity not independently qualified</span> :
              <button key={id} type="button" onClick={() => onVisual(id)}>Open {id}</button>;
          })}
        </li>)}</ul> : <p>No qualified relation is incident to this identity.</p>}
    </section>
    <p className="qualified-boundary">Qualified overlay relations are excluded from canonical Direct Impact.</p>
  </article>;
}
