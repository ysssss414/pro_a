import { useEffect, useState } from "react";
import { getCompanyMaterials, type CompanyMaterial, type CompanyMaterialsPage, type ResearchRouteKind } from "../api/research";

type Navigate = (route: { kind: ResearchRouteKind; id?: string }, values?: Record<string, string>) => void;
const labels: Record<string, string> = {
  uploaded: "Uploaded", processing: "Processing", human_review: "Review required",
  attribution_required: "Attribution required", qualified_unapplied: "Qualified — not applied",
  activated: "Activated / Canonical", failed: "Failed", blocked: "Blocked",
  recovery_required: "Recovery required",
};
const trust: Record<string, string> = {
  company_official: "Official", exchange_official: "Official",
  broker_research: "Broker Research", media: "Media",
  knowledge_community: "Knowledge Community — clue only",
  user_upload: "Unclassified", other: "Unclassified",
};

function Material({ item, companyId, navigate }: { item: CompanyMaterial; companyId: string; navigate: Navigate }) {
  const operations = `/source-operations/${encodeURIComponent(item.source_id)}?company=${encodeURIComponent(companyId)}`;
  return <article className="inspector-row company-material-row">
    <strong>{item.title}</strong>
    <small>{item.title_basis === "operator_title" ? "Operator title" : item.title_basis === "canonical_source" ? "Canonical Source" : "Private filename"} · {item.material_date ?? item.publication_time ?? item.ingested_at ?? item.uploaded_at ?? "Date unknown"}</small>
    <small>{[item.material_kind, item.source_channel ? trust[item.source_channel] : null, labels[item.lifecycle] ?? item.state].filter(Boolean).join(" · ")}</small>
    <small>Association: {item.association_basis.replaceAll("_", " ")}</small>
    {item.processing_scope === "SHARED_CORE" && <small>Processing Scope: Shared Core · Domain Assignment: Pending</small>}
    {item.source_channel === "knowledge_community" && <p className="research-empty">Clue source — verify against primary/official evidence before thesis use. Independent corroboration may be required.</p>}
    {item.canonical ? <>
      <small>{item.claim_count} Claims · {item.linked_node_count} linked Nodes · Potential Current View impact: {item.current_view_impact_candidate_count ?? "unavailable"}</small>
      {!!item.linked_nodes?.length && <div className="inspector-actions">{item.linked_nodes.filter(node => node.node_id !== companyId).map(node =>
        <button key={node.node_id} type="button" onClick={() => navigate({ kind: "node", id: node.node_id })}>{node.canonical_name} · {node.primary_type}</button>)}</div>}
      <div className="inspector-actions"><button type="button" onClick={() => navigate({ kind: "source", id: item.canonical_source_id ?? item.source_id })}>Open Source</button>
        <button type="button" onClick={() => navigate({ kind: "source", id: item.canonical_source_id ?? item.source_id })}>Review Current View Impact</button></div>
    </> : <>
      <small>Private staged material · Impact available after canonical activation.</small>
      <div className="inspector-actions"><a href={operations}>Open Operations</a>
        {item.packet_artifact_id && <a href={`/?surface=review&artifact=${encodeURIComponent(item.packet_artifact_id)}`}>Open Review Workbench</a>}</div>
    </>}
  </article>;
}

export function CompanyMaterialsPanel({ companyId, navigate }: { companyId: string; navigate: Navigate }) {
  const [page, setPage] = useState<CompanyMaterialsPage | null>(null);
  const [items, setItems] = useState<CompanyMaterial[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setItems([]); setNext(null); setExpanded(false); setError("");
    getCompanyMaterials(companyId, null, controller.signal).then(result => {
      if (!controller.signal.aborted) { setPage(result); setItems(result.materials); setNext(result.next_cursor); }
    }).catch(reason => { if (!controller.signal.aborted) setError((reason as Error).message); });
    return () => controller.abort();
  }, [companyId]);
  async function showMore() {
    if (!next) return;
    const controller = new AbortController();
    try {
      const result = await getCompanyMaterials(companyId, next, controller.signal);
      setItems(current => [...current, ...result.materials]); setNext(result.next_cursor);
    } catch (reason) { setError((reason as Error).message); }
  }
  return <section className="research-section unified-section" aria-label="Latest Materials">
    <div className="research-section-heading"><h2>Latest Materials</h2><span>{page?.counts.total ?? "…"}</span></div>
    <p><a href={`/source-operations?company=${encodeURIComponent(companyId)}`}>Add latest material</a></p>
    <p><a href={`/source-operations?company=${encodeURIComponent(companyId)}&community=1`}>Import Knowledge Community</a></p>
    {error ? <p role="alert" className="research-error">{error}</p> : !page ? <p role="status" className="research-empty">Loading company materials…</p>
      : !items.length ? <p className="research-empty">No company materials recorded.</p>
        : (expanded ? items : items.slice(0, 5)).map(item => <Material key={item.material_id} item={item} companyId={companyId} navigate={navigate} />)}
    {items.length > 5 && <button type="button" className="inspector-more" onClick={() => setExpanded(value => !value)}>{expanded ? "Show latest 5" : `Show all ${page?.counts.total ?? items.length} materials`}</button>}
    {expanded && next && <button type="button" className="inspector-more" onClick={() => void showMore()}>Load more materials</button>}
  </section>;
}
