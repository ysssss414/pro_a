import { useEffect, useState } from "react";

import type { CurrentViewResult } from "../api/types";
import { buildCurrentViewPresentation } from "../currentViewPresentation";

interface ViewTabProps {
  currentViews: CurrentViewResult[];
  primaryType?: string;
  loading: boolean;
  error: string | null;
  onOpenSource: (sourceId: string) => void;
}

export function ViewTab({ currentViews, primaryType = "", loading, error, onOpenSource }: ViewTabProps) {
  const [selectedViewId, setSelectedViewId] = useState<string | null>(null);
  useEffect(() => {
    setSelectedViewId(currentViews[0]?.view_id ?? null);
  }, [currentViews]);

  const currentView = currentViews.find((view) => view.view_id === selectedViewId)
    ?? currentViews[0]
    ?? null;
  if (loading && !currentView) return <div className="tab-empty">Loading Current View…</div>;
  if (error) return <div className="tab-empty is-error" role="alert">{error}</div>;
  if (!currentView) return <div className="tab-empty">No official Current View has been recorded for this Node.</div>;

  const presentation = buildCurrentViewPresentation(
    currentView.content_json,
    primaryType,
    currentView.trigger_claim_ids.length,
    Boolean(currentView.trigger_source_id),
    Boolean(currentView.previous_view_id),
  );
  return (
    <div className="tab-content view-tab">
      <article className="current-view-card">
        <div className="view-history-navigation" aria-label="Current View version navigation">
          {currentViews.length === 1 ? (
            <><strong>Initial View</strong><span>No previous revision</span></>
          ) : (
            <>
              <label htmlFor="current-view-version">View version</label>
              <select
                id="current-view-version"
                value={currentView.view_id}
                onChange={(event) => setSelectedViewId(event.target.value)}
              >
                {currentViews.map((view, index) => (
                  <option value={view.view_id} key={view.view_id}>
                    {view.version}{index === 0 ? " — Latest" : ""}
                  </option>
                ))}
              </select>
              <span>{currentView.view_id === currentViews[0].view_id ? "Latest official View" : "Historical official View"}</span>
            </>
          )}
        </div>
        <div className="research-heading-row">
          <div><p className="eyebrow">Governed knowledge state</p><h3>Current View</h3></div>
          <div className="view-version"><strong>{currentView.version}</strong><span>{[currentView.status, currentView.change_level, currentView.revision_date].filter(Boolean).join(" · ")}</span></div>
        </div>
        {presentation.structured ? (
          <div className="current-view-sections">
            {presentation.sections.map((section) => (
              <section className="current-view-section" key={section.title}>
                <h4>{section.title}</h4>
                {Array.isArray(section.value) ? <ul>{section.value.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{section.value}</p>}
              </section>
            ))}
          </div>
        ) : <pre className="current-view-fallback">{currentView.content_md || "No content recorded."}</pre>}
        {presentation.recentChange && <section className="current-view-section"><h4>最近变化</h4><p>{presentation.recentChange}</p></section>}
        <div className="view-evidence-block">
          <strong>证据</strong><span>{presentation.evidenceCount} primary Claims</span>
          {presentation.hasSource && <button type="button" onClick={() => onOpenSource(currentView.trigger_source_id!)}>View Source</button>}
        </div>
        <details className="view-metadata-details">
          <summary>View metadata</summary>
          <dl className="metadata-grid view-metadata">
            <div><dt>Revision date</dt><dd>{currentView.revision_date || "—"}</dd></div>
            <div><dt>Change level</dt><dd>{currentView.change_level || "—"}</dd></div>
            <div><dt>Confirmed</dt><dd>{currentView.confirmed_at || "—"}</dd></div>
            <div><dt>Created</dt><dd>{currentView.created_at || "—"}</dd></div>
            <div><dt>Previous version</dt><dd>{currentView.previous_view_id || "—"}</dd></div>
            <div><dt>View ID</dt><dd>{currentView.view_id}</dd></div>
          </dl>
        </details>
      </article>
    </div>
  );
}
