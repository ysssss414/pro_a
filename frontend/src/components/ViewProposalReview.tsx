import { useEffect, useState } from "react";

import { getViewProposal, getViewProposals } from "../api/client";
import type { ProposalEvidence, ViewProposalDetail, ViewProposalSummary } from "../api/types";
import { buildCurrentViewPresentation } from "../currentViewPresentation";
import { CurrentViewContentChanges } from "./CurrentViewCompare";

function Evidence({ title, items }: { title: string; items: ProposalEvidence[] }) {
  return (
    <section className="current-view-section">
      <h3>{title}</h3>
      {items.length === 0 ? <p>None selected.</p> : <ul className="compare-evidence-list">
        {items.map((item) => <li key={item.claim_id}>
          <strong>{item.resolved ? item.statement : `Unresolved evidence: ${item.claim_id}`}</strong>
          <span>{[item.role ?? "Missing Node link", item.status, item.nature, item.attributed_to, item.source_title]
            .filter(Boolean).join(" · ")}</span>
        </li>)}
      </ul>}
    </section>
  );
}

export function ViewProposalReview({ onOpenSource }: {
  onOpenSource: (sourceId: string, nodeId: string) => void;
}) {
  const [proposals, setProposals] = useState<ViewProposalSummary[]>([]);
  const [offset, setOffset] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ViewProposalDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setListLoading(true);
    setListError(null);
    setProposals([]);
    setSelectedId(null);
    getViewProposals(controller.signal, offset)
      .then((rows) => { if (!controller.signal.aborted) setProposals(rows); })
      .catch(() => { if (!controller.signal.aborted) setListError("Unable to load Human View Proposals."); })
      .finally(() => { if (!controller.signal.aborted) setListLoading(false); });
    return () => controller.abort();
  }, [offset]);

  useEffect(() => {
    const controller = new AbortController();
    setDetail(null);
    setDetailError(null);
    setDetailLoading(selectedId !== null);
    if (selectedId) {
      getViewProposal(selectedId, controller.signal)
        .then((row) => { if (!controller.signal.aborted) setDetail(row); })
        .catch(() => { if (!controller.signal.aborted) setDetailError("Unable to load this Human View Proposal."); })
        .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    }
    return () => controller.abort();
  }, [selectedId]);

  const presentation = detail ? buildCurrentViewPresentation(
    detail.proposed_current_view, detail.node_type, detail.primary_evidence.length,
    detail.trigger_source.resolved, true,
  ) : null;

  return (
    <main className="proposal-workspace">
      <section className="proposal-list-panel" aria-labelledby="proposal-queue-heading">
        <div className="panel-heading"><div><p className="eyebrow">Read-only review</p>
          <h2 id="proposal-queue-heading">Human View Proposals</h2></div></div>
        <p>Pending proposals only. No acceptance action in Phase 2.7B.</p>
        {listLoading && <p role="status">Loading Human View Proposals…</p>}
        {listError && <p role="alert">{listError}</p>}
        {!listLoading && !listError && proposals.length === 0 && (
          <p className="tab-empty">{offset === 0 ? "No pending Human View Proposals" : "No pending Human View Proposals on this page"}</p>
        )}
        <ul className="proposal-list">
          {proposals.map((proposal) => <li key={proposal.proposal_id}>
            <button type="button" aria-pressed={selectedId === proposal.proposal_id} onClick={() => setSelectedId(proposal.proposal_id)}>
              <strong>{proposal.node_name} · {proposal.decision.toUpperCase()}</strong>
              <span>{proposal.created_at} · {proposal.node_type}</span>
              <span>{proposal.reason}</span>
            </button>
          </li>)}
        </ul>
        <nav className="proposal-pagination" aria-label="Proposal pages">
          {offset > 0 && <button type="button" onClick={() => setOffset(Math.max(0, offset - 50))}>Previous page</button>}
          {proposals.length === 50 && <button type="button" onClick={() => setOffset(offset + 50)}>Next page</button>}
        </nav>
      </section>
      <section className="detail-panel proposal-review-detail" aria-label="Human View Proposal detail">
        {!selectedId && <p className="detail-empty">Select a Human View Proposal to review.</p>}
        {detailLoading && <p role="status">Loading Proposal detail…</p>}
        {detailError && <p role="alert">{detailError}</p>}
        {detail && <>
          <div className="panel-heading"><div><p className="eyebrow">{detail.node_type}</p><h2>{detail.node_name}</h2></div></div>
          <p className="proposal-boundary">{detail.status.toUpperCase()} — NOT OFFICIAL CURRENT VIEW</p>
          <p>No acceptance action in Phase 2.7B</p>
          <p className={detail.canonical_alignment === "CURRENT" ? "proposal-alignment" : "proposal-alignment is-stale"}
            role={detail.canonical_alignment === "CURRENT" ? "status" : "alert"}>
            Canonical alignment: <strong>{detail.canonical_alignment}</strong>
            {detail.canonical_alignment !== "CURRENT" && " — Canonical state changed. No automatic rebase or status update."}
          </p>
          <dl className="metadata-grid view-metadata">
            <div><dt>Proposal</dt><dd>{detail.proposal_id}</dd></div>
            <div><dt>Human decision</dt><dd>{detail.decision.toUpperCase()}</dd></div>
            <div><dt>Target official View</dt><dd>{detail.previous_view_id} · {detail.previous_version}</dd></div>
            <div><dt>Created</dt><dd>{detail.created_at}</dd></div>
          </dl>
          <section className="current-view-section"><h3>Human Review reason</h3><p>{detail.reason}</p></section>
          {detail.decision === "thesis" && <section className="current-view-section"><h3>Thesis break</h3>
            <dl><dt>Invalidated core assumption</dt><dd>{detail.thesis_break.invalidated_core_assumption}</dd>
              <dt>Logic chain failure</dt><dd>{detail.thesis_break.logic_chain_failure}</dd>
              <dt>Conclusion change</dt><dd>{detail.thesis_break.conclusion_change}</dd></dl>
          </section>}
          <section className="current-view-section"><h3>Before / Proposed</h3>
            <p>BASE is the stored target official View. Proposed content is not official.</p>
            {detail.diff ? <CurrentViewContentChanges compare={detail.diff} primaryType={detail.node_type} targetLabel="Proposed" />
              : <p role="alert">Target official View unavailable; no comparison can be computed.</p>}
          </section>
          <details className="current-view-section"><summary>Proposed View content</summary>
            {presentation?.sections.map((section) => <section key={section.title}><h4>{section.title}</h4>
              {Array.isArray(section.value) ? <ul>{section.value.map((item, i) => <li key={i}>{item}</li>)}</ul> : <p>{section.value}</p>}
            </section>)}
          </details>
          <Evidence title="Primary Evidence — Subject only" items={detail.primary_evidence} />
          <Evidence title="Context Evidence — Context only" items={detail.context_evidence} />
          <details className="current-view-section"><summary>Candidate Claim-role snapshot ({detail.candidate_claims.length})</summary>
            <ul>{detail.candidate_claims.map((claim) => <li key={claim.claim_id}>{claim.claim_id} · {claim.role}</li>)}</ul>
          </details>
          <section className="current-view-section"><h3>Trigger Source</h3><p>{detail.trigger_source.title}</p>
            <p>{detail.trigger_source.publication_time} · {detail.trigger_source.source_rank} · {detail.trigger_source.origin_type}</p>
            {detail.trigger_source.resolved
              ? <button type="button" onClick={() => onOpenSource(detail.trigger_source_id, detail.node_id)}>Open Source</button>
              : <p>Source no longer available.</p>}
          </section>
        </>}
      </section>
    </main>
  );
}
