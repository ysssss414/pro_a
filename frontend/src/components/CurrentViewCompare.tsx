import type {
  CurrentViewCompareResult,
  CurrentViewDimensionChange,
  CurrentViewEvidenceRef,
  CurrentViewListChange,
} from "../api/types";
import { productDimensionLabel } from "../currentViewPresentation";

interface CurrentViewCompareProps {
  compare: CurrentViewCompareResult;
  primaryType: string;
}

const LIST_LABELS: Record<string, string> = {
  core_logic: "核心逻辑变化",
  core_disagreements: "核心分歧变化",
  assumptions_to_verify: "待验证假设变化",
  major_risks: "主要风险变化",
  knowledge_gaps: "知识缺口变化",
  key_watch_items: "验证点变化",
};

function listLabel(field: string, primaryType: string): string {
  if (field === "key_facts") return primaryType === "Company" ? "关键进展变化" : "关键事实变化";
  return LIST_LABELS[field] ?? field;
}

function DeltaItems({ change }: { change: CurrentViewListChange }) {
  return (
    <div className="compare-delta-columns">
      {change.added.length > 0 && (
        <div><strong>新增</strong><ul>{change.added.map((item) => <li key={`added-${item}`}>{item}</li>)}</ul></div>
      )}
      {change.removed.length > 0 && (
        <div><strong>移除</strong><ul>{change.removed.map((item) => <li key={`removed-${item}`}>{item}</li>)}</ul></div>
      )}
    </div>
  );
}

function DimensionChange({ change }: { change: CurrentViewDimensionChange }) {
  if (change.kind === "list") {
    return <DeltaItems change={{
      added: change.added ?? [],
      removed: change.removed ?? [],
      unchanged: change.unchanged ?? [],
    }} />;
  }
  const renderValue = (value: unknown) => {
    if (value === null || value === undefined || value === "") return "—";
    return typeof value === "string" ? value : JSON.stringify(value);
  };
  return (
    <div className="compare-before-after">
      <div><strong>Before</strong><p>{renderValue(change.before)}</p></div>
      <div><strong>After</strong><p>{renderValue(change.after)}</p></div>
    </div>
  );
}

function EvidenceDetails({ items }: { items: CurrentViewEvidenceRef[] }) {
  return (
    <ul className="compare-evidence-list">
      {items.map((item, index) => (
        <li key={`${item.claim_id}-${index}`}>
          <strong>{item.resolved ? item.statement : "Unresolved evidence reference"}</strong>
          {item.resolved && (
            <span>
              {[item.source_title, item.source_rank && `Rank ${item.source_rank}`, item.status,
                item.confidence === null ? "" : `confidence ${item.confidence}`].filter(Boolean).join(" · ")}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

export function CurrentViewCompare({ compare, primaryType }: CurrentViewCompareProps) {
  const changedScalars = compare.scalar_changes.filter((change) => change.changed);
  const changedLists = Object.entries(compare.list_changes)
    .filter(([, change]) => change.added.length > 0 || change.removed.length > 0);
  const changedDimensions = Object.entries(compare.type_specific_changes)
    .filter(([, change]) => change.status !== "unchanged");
  return (
    <div className="current-view-compare" aria-label="Current View comparison">
      {!compare.has_changes && <p className="tab-empty">No exact structured changes.</p>}

      {changedScalars.map((change) => (
        <section className="current-view-section" key={change.field}>
          <h4>{change.field === "one_line_conclusion"
            ? "当前判断"
            : primaryType === "Company" ? "投资逻辑变化" : "投资含义变化"}</h4>
          <div className="compare-before-after">
            <div><strong>Before</strong><p>{change.before || "—"}</p></div>
            <div><strong>After</strong><p>{change.after || "—"}</p></div>
          </div>
        </section>
      ))}

      {changedLists.map(([field, change]) => (
        <section className="current-view-section" key={field}>
          <h4>{listLabel(field, primaryType)}</h4>
          <DeltaItems change={change} />
        </section>
      ))}

      {changedDimensions.length > 0 && (
        <section className="current-view-section">
          <h4>专业维度变化</h4>
          <div className="compare-dimension-list">
            {changedDimensions.map(([key, change]) => (
              <div key={key}>
                <strong>{productDimensionLabel(key)}</strong>
                <span>{change.status}</span>
                <DimensionChange change={change} />
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="current-view-section">
        <h4>Evidence Delta</h4>
        <div className="compare-evidence-summary">
          <details>
            <summary>新增证据 {compare.evidence.added.length} 条</summary>
            <EvidenceDetails items={compare.evidence.added} />
          </details>
          <details>
            <summary>移除证据 {compare.evidence.removed.length} 条</summary>
            <EvidenceDetails items={compare.evidence.removed} />
          </details>
        </div>
      </section>

      <section className="current-view-section">
        <h4>Governance metadata</h4>
        <dl className="metadata-grid view-metadata">
          <div><dt>BASE change level</dt><dd>{compare.base.change_level || "—"}</dd></div>
          <div><dt>TARGET change level</dt><dd>{compare.target.change_level || "—"}</dd></div>
          <div><dt>Trigger Source</dt><dd>{compare.trigger_source_change.status}</dd></div>
          <div><dt>TARGET previous View</dt><dd>{compare.target.previous_view_id || "—"}</dd></div>
        </dl>
        {compare.target.recent_change && (
          <div className="compare-stored-change"><strong>TARGET stored recent_change</strong><p>{compare.target.recent_change}</p></div>
        )}
      </section>
    </div>
  );
}
