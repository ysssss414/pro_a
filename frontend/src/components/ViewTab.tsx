import { useEffect, useState } from "react";

import { getCurrentViewCompare } from "../api/client";
import type { CurrentViewCompareResult, CurrentViewResult } from "../api/types";
import { buildCurrentViewPresentation } from "../currentViewPresentation";
import { CurrentViewCompare } from "./CurrentViewCompare";

interface ViewTabProps {
  currentViews: CurrentViewResult[];
  primaryType?: string;
  loading: boolean;
  error: string | null;
  onOpenSource: (sourceId: string) => void;
}

export function ViewTab({ currentViews, primaryType = "", loading, error, onOpenSource }: ViewTabProps) {
  const [selectedViewId, setSelectedViewId] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [baseViewId, setBaseViewId] = useState("");
  const [targetViewId, setTargetViewId] = useState("");
  const [compare, setCompare] = useState<CurrentViewCompareResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const nodeId = currentViews[0]?.node_id ?? "";
  const comparePairAvailable = currentViews.some((view) => view.view_id === baseViewId)
    && currentViews.some((view) => view.view_id === targetViewId);

  useEffect(() => {
    setSelectedViewId(currentViews[0]?.view_id ?? null);
    setCompareMode(false);
    setBaseViewId("");
    setTargetViewId("");
    setCompare(null);
    setCompareError(null);
  }, [currentViews]);

  useEffect(() => {
    if (!compareMode || !nodeId || !comparePairAvailable) return;
    const controller = new AbortController();
    setCompare(null);
    setCompareError(null);
    setCompareLoading(true);
    const loadCompare = async () => {
      try {
        const result = await getCurrentViewCompare(nodeId, baseViewId, targetViewId, controller.signal);
        if (!controller.signal.aborted) setCompare(result);
      } catch (reason) {
        if ((reason as Error).name !== "AbortError" && !controller.signal.aborted) {
          setCompareError("Unable to load Current View comparison.");
        }
      } finally {
        if (!controller.signal.aborted) setCompareLoading(false);
      }
    };
    void loadCompare();
    return () => controller.abort();
  }, [baseViewId, compareMode, comparePairAvailable, nodeId, targetViewId]);

  const currentView = currentViews.find((view) => view.view_id === selectedViewId)
    ?? currentViews[0]
    ?? null;
  if (loading && !currentView) return <div className="tab-empty">Loading Current View…</div>;
  if (error) return <div className="tab-empty is-error" role="alert">{error}</div>;
  if (!currentView) return <div className="tab-empty">No official Current View has been recorded for this Node.</div>;

  const previousOfficialView = (targetId: string): CurrentViewResult | null => {
    const targetIndex = currentViews.findIndex((view) => view.view_id === targetId);
    if (targetIndex < 0) return null;
    const direct = currentViews.find((view) => view.view_id === currentViews[targetIndex].previous_view_id);
    const directIndex = direct ? currentViews.findIndex((view) => view.view_id === direct.view_id) : -1;
    if (direct && directIndex > targetIndex) return direct;
    return currentViews[targetIndex + 1] ?? null;
  };
  const previousView = previousOfficialView(currentView.view_id);

  const enterCompare = () => {
    if (!previousView) return;
    setBaseViewId(previousView.view_id);
    setTargetViewId(currentView.view_id);
    setCompareMode(true);
  };

  if (compareMode) {
    const targetIndex = currentViews.findIndex((view) => view.view_id === targetViewId);
    const baseOptions = targetIndex < 0 ? [] : currentViews.slice(targetIndex + 1);
    const baseView = currentViews.find((view) => view.view_id === baseViewId);
    const targetView = currentViews.find((view) => view.view_id === targetViewId);
    return (
      <div className="tab-content view-tab">
        <article className="current-view-card">
          <div className="view-compare-navigation" aria-label="Current View comparison controls">
            <label htmlFor="compare-base-version">BASE version</label>
            <select
              id="compare-base-version"
              value={baseViewId}
              onChange={(event) => setBaseViewId(event.target.value)}
            >
              {baseOptions.map((view) => <option key={view.view_id} value={view.view_id}>{view.version}</option>)}
            </select>
            <span aria-hidden="true">→</span>
            <label htmlFor="compare-target-version">TARGET version</label>
            <select
              id="compare-target-version"
              value={targetViewId}
              onChange={(event) => {
                const nextTarget = event.target.value;
                const nextBase = previousOfficialView(nextTarget);
                setTargetViewId(nextTarget);
                setSelectedViewId(nextTarget);
                setBaseViewId(nextBase?.view_id ?? "");
              }}
            >
              {currentViews.slice(0, -1).map((view) => <option key={view.view_id} value={view.view_id}>{view.version}</option>)}
            </select>
            <button type="button" onClick={() => setCompareMode(false)}>Exit Compare</button>
          </div>
          <div className="research-heading-row">
            <div><p className="eyebrow">Deterministic structured diff</p><h3>Current View Compare</h3></div>
            <div className="view-version compare-version-pair">
              <strong>{baseView?.version ?? "—"} → {targetView?.version ?? "—"}</strong>
              <span>BASE → TARGET</span>
            </div>
          </div>
          {compareLoading && <div className="tab-empty">Loading comparison…</div>}
          {compareError && <div className="tab-empty is-error" role="alert">{compareError}</div>}
          {compare && <CurrentViewCompare compare={compare} primaryType={primaryType} />}
        </article>
      </div>
    );
  }

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
            <><strong>Initial View</strong><span>No previous revision to compare</span></>
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
              {previousView
                ? <button type="button" onClick={enterCompare}>Compare with previous</button>
                : <span>No previous revision to compare</span>}
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
