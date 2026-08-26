import type {
  KnowledgeGapResult,
  ResearchClaimSummary,
  ResearchQuestionResult,
} from "../api/types";

interface ResearchTabProps {
  researchQuestion: ResearchQuestionResult | null;
  knowledgeGaps: KnowledgeGapResult[];
  loading: boolean;
  researchError: string | null;
  gapsError: string | null;
}

function formatConfidence(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function variableLabel(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}: ${typeof item === "object" ? JSON.stringify(item) : String(item)}`)
      .join(" · ");
  }
  return JSON.stringify(value);
}

function EvidenceList({ title, claims }: { title: string; claims: ResearchClaimSummary[] }) {
  return (
    <section className="research-evidence">
      <h4>{title}</h4>
      {claims.length === 0 ? (
        <p className="empty-inline">None recorded.</p>
      ) : (
        claims.map((claim) => (
          <article key={claim.claim_id}>
            <p>{claim.statement || "Referenced Claim is unavailable."}</p>
            <div>
              <code>{claim.claim_id}</code>
              <span>{claim.status || "missing"}</span>
              <span>{formatConfidence(claim.confidence)}</span>
            </div>
          </article>
        ))
      )}
    </section>
  );
}

function ResearchQuestion({ question }: { question: ResearchQuestionResult }) {
  return (
    <article className="research-question-card">
      <div className="research-heading-row">
        <div>
          <p className="eyebrow">Research Question</p>
          <h3>{question.question}</h3>
        </div>
        <span className="status-badge">{question.status}</span>
      </div>

      <section className="current-answer">
        <h4>Current Answer</h4>
        <p>{question.current_answer || "No current answer recorded."}</p>
      </section>

      <dl className="metadata-grid research-metadata">
        <div><dt>Confidence</dt><dd>{formatConfidence(question.confidence)}</dd></div>
        <div><dt>Importance</dt><dd>{question.importance || "—"}</dd></div>
      </dl>

      <section className="key-variables">
        <h4>Key Variables</h4>
        {question.key_variables.length === 0 ? (
          <p className="empty-inline">None recorded.</p>
        ) : (
          <div>{question.key_variables.map((variable, index) => (
            <span key={`${variableLabel(variable)}-${index}`}>{variableLabel(variable)}</span>
          ))}</div>
        )}
      </section>

      <section className="change-mind-block">
        <h4>What would change my mind</h4>
        <p>{question.what_would_change_my_mind || "Not recorded."}</p>
      </section>

      <div className="evidence-grid">
        <EvidenceList title="Supporting Evidence" claims={question.supporting_claims} />
        <EvidenceList title="Opposing Evidence" claims={question.opposing_claims} />
      </div>
      <code>{question.rq_id}</code>
    </article>
  );
}

function gapTone(status: string): string {
  if (["open", "reopened", "needs_refresh"].includes(status)) return "is-active";
  if (["closed", "resolved", "superseded"].includes(status)) return "is-subdued";
  return "";
}

export function ResearchTab({
  researchQuestion,
  knowledgeGaps,
  loading,
  researchError,
  gapsError,
}: ResearchTabProps) {
  return (
    <div className="tab-content research-tab">
      {loading && !researchQuestion && <div className="inline-loading">Loading research state…</div>}
      {researchError ? (
        <div className="module-error" role="alert">{researchError}</div>
      ) : !loading && !researchQuestion ? (
        <div className="tab-empty compact">No Research Question has been recorded for this Node.</div>
      ) : researchQuestion ? (
        <ResearchQuestion question={researchQuestion} />
      ) : null}

      <section className="knowledge-gaps-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Uncertainty register</p>
            <h3>Knowledge Gaps</h3>
          </div>
          <span className="count-label">{knowledgeGaps.length}</span>
        </div>
        {gapsError ? (
          <div className="module-error" role="alert">{gapsError}</div>
        ) : !loading && knowledgeGaps.length === 0 ? (
          <div className="tab-empty compact">No Knowledge Gaps are recorded for this Node.</div>
        ) : (
          <div className="gap-list">
            {knowledgeGaps.map((gap) => (
              <article className={`gap-card ${gapTone(gap.status)}`} key={gap.gap_id}>
                <div className="gap-card-heading">
                  <h4>{gap.title}</h4>
                  <span>{gap.status}</span>
                </div>
                <p>{gap.description || "No description recorded."}</p>
                <dl className="metadata-grid gap-metadata">
                  <div><dt>Freshness due</dt><dd>{gap.freshness_due || "—"}</dd></div>
                  <div><dt>Resolution Claim</dt><dd>{gap.resolution_claim_id || "—"}</dd></div>
                  <div><dt>Superseded by</dt><dd>{gap.superseded_by_gap_id || "—"}</dd></div>
                </dl>
                {gap.source_claim_ids.length > 0 && (
                  <div className="id-list">{gap.source_claim_ids.map((id) => <code key={id}>{id}</code>)}</div>
                )}
                <code>{gap.gap_id}</code>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
