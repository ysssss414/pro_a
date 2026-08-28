import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";

import { getCurrentView } from "../api/client";
import type { CurrentViewResult, ImpactCandidate, SourceDetail } from "../api/types";
import { buildCurrentViewPresentation } from "../currentViewPresentation";
import {
  DECISIONS,
  DECISION_LABELS,
  buildReviewArtifact,
  createReviewDraft,
  downloadReviewArtifact,
  isPrimaryEligible,
  loadReviewDraft,
  reviewClaims,
  saveReviewDraft,
  validateReviewDraft,
  type HumanImpactDecision,
  type HumanImpactReviewDraft,
  type ReviewClaim,
} from "../humanImpactReview";

interface HumanImpactReviewProps {
  source: SourceDetail;
  candidate: ImpactCandidate;
  onCancel: () => void;
  onOpenView: (nodeId: string) => void;
}

function formatConfidence(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function roleLabel(role: ReviewClaim["role"]): string {
  return role === "subject" ? "Subject" : role === "context" ? "Context only" : "Association only";
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

function updateDraft(
  setDraft: Dispatch<SetStateAction<HumanImpactReviewDraft | null>>,
  update: (draft: HumanImpactReviewDraft) => HumanImpactReviewDraft,
) {
  setDraft((current) => current ? update(current) : current);
}

export function HumanImpactReview({ source, candidate, onCancel, onOpenView }: HumanImpactReviewProps) {
  const [currentView, setCurrentView] = useState<CurrentViewResult | null>(null);
  const [draft, setDraft] = useState<HumanImpactReviewDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const claims = useMemo(() => reviewClaims(source, candidate), [candidate, source]);

  useEffect(() => {
    const controller = new AbortController();
    setCurrentView(null);
    setDraft(null);
    setLoading(true);
    setError(null);
    setSavedMessage(null);
    getCurrentView(candidate.node.node_id, controller.signal)
      .then((view) => {
        if (controller.signal.aborted) return;
        if (!view) {
          setError("No latest official Current View is available for this candidate.");
          return;
        }
        setCurrentView(view);
        setDraft(loadReviewDraft(source.source_id, candidate.node.node_id, view.view_id)
          ?? createReviewDraft(source, candidate, view));
      })
      .catch((requestError) => {
        if ((requestError as Error).name !== "AbortError") {
          setError("Unable to load the target Current View.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [candidate.node.node_id, source, candidate]);

  const validation = draft && currentView
    ? validateReviewDraft(draft, candidate, currentView)
    : null;
  const presentation = currentView
    ? buildCurrentViewPresentation(
      currentView.content_json,
      candidate.node.primary_type,
      currentView.trigger_claim_ids.length,
      Boolean(currentView.trigger_source_id),
      Boolean(currentView.previous_view_id),
    )
    : null;

  const handleSave = () => {
    if (!draft || !validation) return;
    const nextDraft = { ...draft, status: validation.status, updated_at: new Date().toISOString() };
    setDraft(nextDraft);
    setSavedMessage(saveReviewDraft(nextDraft)
      ? "Local draft saved — not canonical."
      : "Unable to save the local draft in this browser.");
  };

  const handleExport = () => {
    if (!draft || !validation?.ready) return;
    downloadReviewArtifact(buildReviewArtifact(draft, source));
    setSavedMessage("Review JSON exported locally — not canonical.");
  };

  const handleOpenView = () => {
    if (draft) saveReviewDraft({ ...draft, status: validation?.status ?? "DRAFT" });
    onOpenView(candidate.node.node_id);
  };

  const setDecision = (decision: HumanImpactDecision) => {
    updateDraft(setDraft, (current) => ({ ...current, decision }));
    setSavedMessage(null);
  };

  const setReason = (reason: string) => {
    updateDraft(setDraft, (current) => ({ ...current, reason }));
    setSavedMessage(null);
  };

  const setThesisField = (field: keyof HumanImpactReviewDraft["thesis_break"], value: string) => {
    updateDraft(setDraft, (current) => ({
      ...current,
      thesis_break: { ...current.thesis_break, [field]: value },
    }));
    setSavedMessage(null);
  };

  const togglePrimary = (claimId: string) => {
    updateDraft(setDraft, (current) => ({
      ...current,
      selected_primary_claim_ids: toggleValue(current.selected_primary_claim_ids, claimId),
    }));
    setSavedMessage(null);
  };

  const toggleContext = (claimId: string) => {
    updateDraft(setDraft, (current) => ({
      ...current,
      selected_context_claim_ids: toggleValue(current.selected_context_claim_ids, claimId),
    }));
    setSavedMessage(null);
  };

  return (
    <section className="detail-panel human-impact-review" aria-labelledby="human-impact-review-heading">
      <div className="panel-heading source-detail-toolbar">
        <button type="button" className="back-button" onClick={onCancel}>← Back to Source</button>
        <div>
          <p className="eyebrow">Non-canonical human handoff</p>
          <h2 id="human-impact-review-heading">Human Impact Review</h2>
        </div>
      </div>

      <div className="human-impact-review-content">
        <div className="local-draft-banner" role="note">
          Local draft — not canonical. Nothing here writes Production knowledge, impact reviews, proposals, or Current Views.
        </div>

        {loading && <div className="detail-empty"><p>Loading target Current View…</p></div>}
        {error && <div className="detail-empty is-error" role="alert"><p>{error}</p></div>}

        {!loading && !error && draft && currentView && (
          <>
            <section className="review-section">
              <h3>Source</h3>
              <dl className="source-metadata review-metadata">
                <div><dt>Title</dt><dd>{source.title}</dd></div>
                <div><dt>Published</dt><dd>{source.publication_time || "—"}</dd></div>
                <div><dt>Source rank</dt><dd>{source.source_rank || "—"}</dd></div>
                <div><dt>Type / origin</dt><dd>{[source.source_type, source.origin_type].filter(Boolean).join(" · ") || "—"}</dd></div>
              </dl>
            </section>

            <section className="review-section">
              <div className="review-section-heading">
                <h3>Target</h3>
                <span className={`review-status status-${validation?.status.toLowerCase() ?? "draft"}`}>
                  {validation?.status ?? "DRAFT"}
                </span>
              </div>
              <div className="review-target-card">
                <div>
                  <strong>{candidate.node.canonical_name}</strong>
                  <span>{candidate.node.primary_type} · {currentView.version}</span>
                  <small>{currentView.revision_date || "—"}</small>
                </div>
                <button type="button" onClick={handleOpenView}>Open Current View</button>
              </div>
            </section>

            {validation?.status === "STALE" && (
              <div className="review-warning" role="alert">
                {validation.issues.filter((issue) => issue === "STALE TARGET VIEW" || issue === "CANDIDATE EVIDENCE CHANGED").map((issue) => (
                  <strong key={issue}>{issue}</strong>
                ))}
                <span>This review cannot be exported until the candidate is reviewed again.</span>
              </div>
            )}

            <section className="review-section">
              <h3>Existing View</h3>
              {presentation?.sections.length ? (
                <div className="review-existing-view">
                  {presentation.sections.map((section) => (
                    <div key={section.title}>
                      <strong>{section.title}</strong>
                      {Array.isArray(section.value)
                        ? <ul>{section.value.map((item) => <li key={item}>{item}</li>)}</ul>
                        : <p>{section.value}</p>}
                    </div>
                  ))}
                  {presentation.recentChange && (
                    <div>
                      <strong>最近变化</strong>
                      <p>{presentation.recentChange}</p>
                    </div>
                  )}
                </div>
              ) : <pre className="current-view-fallback">{currentView.content_md || "No content recorded."}</pre>}
            </section>

            <section className="review-section">
              <h3>New Evidence</h3>
              <p className="review-help">Select Subject Claims only when they are eligible for Primary Evidence. Context and Related Claims cannot become Primary Evidence.</p>
              {(["subject", "context", "related"] as const).map((role) => {
                const roleClaims = claims.filter((claim) => claim.role === role);
                if (!roleClaims.length) return null;
                return (
                  <fieldset className="review-claim-group" key={role}>
                    <legend>{role === "subject" ? "Subject Claims" : role === "context" ? "Context Claims" : "Related Claims"}</legend>
                    {roleClaims.map((claim) => {
                      const primaryEligible = isPrimaryEligible(claim);
                      const selected = role === "subject"
                        ? draft.selected_primary_claim_ids.includes(claim.claim_id)
                        : role === "context" && draft.selected_context_claim_ids.includes(claim.claim_id);
                      return (
                        <article className="review-claim-card" key={claim.claim_id}>
                          <div className="review-claim-select">
                            {role === "subject" && (
                              <input
                                type="checkbox"
                                aria-label={`Select primary evidence: ${claim.statement}`}
                                checked={selected}
                                disabled={!primaryEligible}
                                onChange={() => togglePrimary(claim.claim_id)}
                              />
                            )}
                            {role === "context" && (
                              <input
                                type="checkbox"
                                aria-label={`Select context evidence: ${claim.statement}`}
                                checked={selected}
                                onChange={() => toggleContext(claim.claim_id)}
                              />
                            )}
                            <div>
                              <strong>{claim.statement}</strong>
                              <span className="review-role-label">{roleLabel(claim.role)}</span>
                            </div>
                          </div>
                          <dl className="metadata-grid review-claim-metadata">
                            <div><dt>Nature</dt><dd>{claim.nature}</dd></div>
                            <div><dt>Status</dt><dd>{claim.status || "—"}</dd></div>
                            <div><dt>Confidence</dt><dd>{formatConfidence(claim.confidence)}</dd></div>
                            <div><dt>Fact time</dt><dd>{claim.fact_time || "—"}</dd></div>
                            <div><dt>Published</dt><dd>{claim.publication_time || "—"}</dd></div>
                            <div><dt>Attribution</dt><dd>{claim.attributed_to || "—"}</dd></div>
                          </dl>
                          {role === "subject" && !primaryEligible && <small className="review-disabled-note">Not eligible for Primary Evidence</small>}
                          {claim.evidence_excerpt && <blockquote>{claim.evidence_excerpt}</blockquote>}
                        </article>
                      );
                    })}
                  </fieldset>
                );
              })}
            </section>

            <section className="review-section">
              <h3>Decision</h3>
              <fieldset className="decision-options">
                <legend className="visually-hidden">Human impact decision</legend>
                {DECISIONS.map((decision) => (
                  <label key={decision}>
                    <input
                      type="radio"
                      name="human-impact-decision"
                      value={decision}
                      checked={draft.decision === decision}
                      onChange={() => setDecision(decision)}
                    />
                    <span>{DECISION_LABELS[decision]}</span>
                  </label>
                ))}
              </fieldset>
              {draft.decision === "MATERIAL" && (
                <div className="governance-reminder">
                  Material 通常要求：一条直接高可信 Primary Evidence；或两条以上独立且较高可信 Evidence；或核心假设被实际结果直接验证/证伪。<br />Evidence Sufficiency = NOT_EVALUATED
                </div>
              )}
              {draft.decision === "THESIS" && (
                <div className="governance-reminder">
                  Thesis Change 通常要求：决定性 Primary Evidence；或至少两条独立高质量 Evidence。必须解释核心假设失效 → 逻辑链失效 → 最终结论改变。<br />Evidence Sufficiency = NOT_EVALUATED
                </div>
              )}
            </section>

            <section className="review-section">
              <h3>Reason</h3>
              <textarea
                aria-label="Reason"
                value={draft.reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Explain the human judgment for this Source → Node review."
                rows={4}
                required
              />
              {draft.decision === "THESIS" && (
                <div className="thesis-reason-fields">
                  <label>Invalidated core assumption<input value={draft.thesis_break.invalidated_core_assumption} onChange={(event) => setThesisField("invalidated_core_assumption", event.target.value)} /></label>
                  <label>Logic-chain failure<input value={draft.thesis_break.logic_chain_failure} onChange={(event) => setThesisField("logic_chain_failure", event.target.value)} /></label>
                  <label>Conclusion change<input value={draft.thesis_break.conclusion_change} onChange={(event) => setThesisField("conclusion_change", event.target.value)} /></label>
                </div>
              )}
              {validation && validation.issues.length > 0 && (
                <ul className="review-validation" role="alert">
                  {validation.issues.map((issue) => <li key={issue}>{issue}</li>)}
                </ul>
              )}
            </section>

            <div className="review-actions">
              <button type="button" onClick={handleSave}>Save Draft Locally</button>
              <button type="button" onClick={handleExport} disabled={!validation?.ready}>Export Review JSON</button>
              <button type="button" className="back-button" onClick={onCancel}>Cancel</button>
            </div>
            {savedMessage && <p className="review-saved-message" role="status">{savedMessage}</p>}
          </>
        )}
      </div>
    </section>
  );
}
