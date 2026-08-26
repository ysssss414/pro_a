import type { CurrentViewResult } from "../api/types";

interface ViewTabProps {
  currentView: CurrentViewResult | null;
  loading: boolean;
  error: string | null;
  onOpenSource: (sourceId: string) => void;
}

export function ViewTab({ currentView, loading, error, onOpenSource }: ViewTabProps) {
  if (loading && !currentView) {
    return <div className="tab-empty">Loading Current View…</div>;
  }
  if (error) {
    return <div className="tab-empty is-error" role="alert">{error}</div>;
  }
  if (!currentView) {
    return <div className="tab-empty">No official Current View has been recorded for this Node.</div>;
  }

  return (
    <div className="tab-content view-tab">
      <article className="current-view-card">
        <div className="research-heading-row">
          <div>
            <p className="eyebrow">Governed knowledge state</p>
            <h3>Current View</h3>
          </div>
          <div className="view-version">
            <strong>{currentView.version}</strong>
            <span>{currentView.status}</span>
          </div>
        </div>

        <div className="current-view-content">{currentView.content_md || "No content recorded."}</div>

        <dl className="metadata-grid view-metadata">
          <div><dt>Change level</dt><dd>{currentView.change_level || "—"}</dd></div>
          <div><dt>Revision</dt><dd>{currentView.revision_date || "—"} · seq {currentView.revision_seq}</dd></div>
          <div><dt>Confirmed</dt><dd>{currentView.confirmed_at || "—"}</dd></div>
          <div><dt>Created</dt><dd>{currentView.created_at || "—"}</dd></div>
          <div><dt>Previous version</dt><dd>{currentView.previous_view_id || "—"}</dd></div>
          <div><dt>Accepted proposal</dt><dd>{currentView.accepted_proposal_id || "—"}</dd></div>
        </dl>

        {(currentView.trigger_source_id || currentView.trigger_claim_ids.length > 0) && (
          <div className="trigger-block">
            <h4>Triggered by</h4>
            {currentView.trigger_source_id && (
              <button type="button" onClick={() => onOpenSource(currentView.trigger_source_id!)}>
                View Source
              </button>
            )}
            {currentView.trigger_claim_ids.length > 0 && (
              <div className="id-list">
                {currentView.trigger_claim_ids.map((claimId) => <code key={claimId}>{claimId}</code>)}
              </div>
            )}
          </div>
        )}
        <code>{currentView.view_id}</code>
      </article>
    </div>
  );
}
