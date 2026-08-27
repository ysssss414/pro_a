import { useEffect, useState } from "react";

import { getSourceImpactCandidates } from "../api/client";
import type { SourceDetail, SourceImpactCandidatesResult } from "../api/types";

interface SourceDetailPanelProps {
  sourceId: string;
  source: SourceDetail | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onSelectNode: (nodeId: string) => void;
  onOpenView: (nodeId: string) => void;
}

function formatConfidence(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function SourceDetailPanel({
  sourceId,
  source,
  loading,
  error,
  onBack,
  onSelectNode,
  onOpenView,
}: SourceDetailPanelProps) {
  const [impact, setImpact] = useState<SourceImpactCandidatesResult | null>(null);
  const [impactLoading, setImpactLoading] = useState(true);
  const [impactError, setImpactError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setImpact(null);
    setImpactLoading(true);
    setImpactError(null);
    getSourceImpactCandidates(sourceId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setImpact(result);
      })
      .catch((requestError) => {
        if ((requestError as Error).name !== "AbortError") {
          setImpactError("Unable to load direct Current View candidates.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setImpactLoading(false);
      });
    return () => controller.abort();
  }, [sourceId]);

  return (
    <section className="detail-panel source-detail-panel" aria-labelledby="source-detail-heading">
      <div className="panel-heading source-detail-toolbar">
        <button type="button" className="back-button" onClick={onBack}>← Back to Node</button>
        <div>
          <p className="eyebrow">Structured provenance</p>
          <h2 id="source-detail-heading">Source Detail</h2>
        </div>
      </div>

      {loading && <div className="detail-empty"><p>Loading Source…</p></div>}
      {error && <div className="detail-empty is-error" role="alert"><p>{error}</p></div>}
      {!loading && !error && !source && (
        <div className="detail-empty"><p>No Source detail available.</p><code>{sourceId}</code></div>
      )}

      {source && (
        <div className="source-detail-content">
          <article className="source-identity-card">
            <div className="source-card-heading">
              <div>
                <span className="type-badge">{source.source_type}</span>
                <h3>{source.title}</h3>
              </div>
              <span className="rank-badge">Rank {source.source_rank}</span>
            </div>
            <dl className="source-metadata">
              <div><dt>Organization</dt><dd>{source.organization || "—"}</dd></div>
              <div><dt>Author</dt><dd>{source.author || "—"}</dd></div>
              <div><dt>Published</dt><dd>{source.publication_time || "—"}</dd></div>
              <div><dt>Original file</dt><dd>{source.original_name || "—"}</dd></div>
              <div><dt>Source rank</dt><dd>{source.source_rank || "—"}</dd></div>
              <div><dt>Origin</dt><dd>{source.origin_type || "—"}</dd></div>
              <div><dt>Ingestion</dt><dd>{source.ingestion_mode || "—"}</dd></div>
              <div><dt>Analysis</dt><dd>{source.analysis_mode || "—"}</dd></div>
              <div><dt>Status</dt><dd>{source.status || "—"}</dd></div>
              <div><dt>Ingested</dt><dd>{source.ingested_at || "—"}</dd></div>
            </dl>
            <code>{source.source_id}</code>
          </article>

          <section className="source-detail-section">
            <div className="section-title-row">
              <h3>Linked Nodes</h3>
              <span className="count-label">{source.linked_nodes.length}</span>
            </div>
            {source.linked_nodes.length === 0 ? (
              <p className="empty-inline">No direct Node links.</p>
            ) : source.linked_nodes.map((node) => (
              <article className="source-node-link" key={node.node_id}>
                <button
                  type="button"
                  aria-label={`${node.canonical_name} ${node.primary_type}`}
                  onClick={() => onSelectNode(node.node_id)}
                >
                  <strong>{node.canonical_name}</strong>
                  <span>{node.primary_type}</span>
                </button>
                <div><span>Role: {node.role}</span><span>Origin: {node.link_origin}</span><span>{formatConfidence(node.confidence)}</span></div>
                {node.evidence_excerpt && <blockquote>{node.evidence_excerpt}</blockquote>}
              </article>
            ))}
          </section>

          <section className="source-detail-section">
            <div className="section-title-row">
              <h3>Claims from this Source</h3>
              <span className="count-label">{source.claims.length}</span>
            </div>
            {source.claims.length === 0 ? (
              <p className="empty-inline">No Claims belong to this Source.</p>
            ) : source.claims.map((claim) => (
              <article className="source-claim-card" key={claim.claim_id}>
                <div className="card-badges"><span>{claim.nature}</span><span>{claim.status}</span><span>{formatConfidence(claim.confidence)}</span></div>
                <h4>{claim.statement}</h4>
                <blockquote>{claim.evidence_excerpt || "No evidence excerpt recorded."}</blockquote>
                {claim.linked_nodes.length > 0 && (
                  <div className="claim-node-links">
                    <span>Linked Nodes</span>
                    {claim.linked_nodes.map((node) => (
                      <button type="button" key={node.node_id} onClick={() => onSelectNode(node.node_id)}>
                        {node.canonical_name} · {node.role}
                      </button>
                    ))}
                  </div>
                )}
                <code>{claim.claim_id}</code>
              </article>
            ))}
          </section>

          <section className="source-detail-section impact-review-section">
            <div className="section-title-row">
              <h3>Potential Current View Impact</h3>
              {impact && <span className="count-label">{impact.candidates.length} Views to review</span>}
            </div>
            <p className="impact-scope-note">Directly linked through Claims</p>
            {impactLoading && <p className="empty-inline">Loading direct candidates…</p>}
            {impactError && <p className="module-error" role="alert">{impactError}</p>}
            {impact && impact.candidates.length === 0 && (
              <p className="empty-inline">No directly linked Current Views</p>
            )}
            {impact?.candidates.map((candidate) => (
              <article className="impact-candidate-card" key={candidate.node.node_id}>
                <div className="impact-candidate-heading">
                  <div><h4>{candidate.node.canonical_name}</h4><span>{candidate.node.primary_type}</span></div>
                  <button type="button" onClick={() => onOpenView(candidate.node.node_id)}>Open View</button>
                </div>
                <p>{candidate.claims.length} linked Claims</p>
                <div className="impact-candidate-meta">
                  {candidate.roles.map((role) => <span key={role}>Attribution role: {role}</span>)}
                  <span>Current View {candidate.current_view.version}</span>
                  <span>Revised {candidate.current_view.revision_date || "—"}</span>
                </div>
              </article>
            ))}
            {impact && impact.linked_nodes_without_current_view.length > 0 && (
              <div className="impact-without-view">
                <h4>Linked Nodes without Current View</h4>
                {impact.linked_nodes_without_current_view.map((item) => (
                  <article className="impact-candidate-card" key={item.node.node_id}>
                    <div className="impact-candidate-heading">
                      <div><h4>{item.node.canonical_name}</h4><span>{item.node.primary_type}</span></div>
                    </div>
                    <p>{item.claims.length} linked Claims</p>
                    <div className="impact-candidate-meta">
                      {item.roles.map((role) => <span key={role}>Attribution role: {role}</span>)}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
