import type {
  ClaimResult,
  CurrentViewResult,
  KnowledgeGapResult,
  NodeDetail,
  NodeSource,
  NodeSummary,
  RelationResult,
  ResearchQuestionResult,
  SourceDetail,
} from "../api/types";
import { ResearchTab } from "./ResearchTab";
import { SourceDetailPanel } from "./SourceDetailPanel";
import { ViewTab } from "./ViewTab";

export type DetailTab = "overview" | "view" | "research" | "claims" | "sources";

export interface KnowledgeErrors {
  claims: string | null;
  sources: string | null;
  view: string | null;
  research: string | null;
  gaps: string | null;
}

interface NodeDetailPanelProps {
  selectedNodeId: string | null;
  detail: NodeDetail | null;
  claims: ClaimResult[];
  sources: NodeSource[];
  currentView: CurrentViewResult | null;
  researchQuestion: ResearchQuestionResult | null;
  knowledgeGaps: KnowledgeGapResult[];
  activeTab: DetailTab;
  loading: boolean;
  knowledgeLoading: boolean;
  error: string | null;
  knowledgeErrors: KnowledgeErrors;
  selectedSourceId: string | null;
  sourceDetail: SourceDetail | null;
  sourceLoading: boolean;
  sourceError: string | null;
  onTabChange: (tab: DetailTab) => void;
  onSelect: (nodeId: string) => void;
  onOpenSource: (sourceId: string) => void;
  onCloseSource: () => void;
}

function formatConfidence(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function NodeLinks({
  title,
  nodes,
  onSelect,
}: {
  title: string;
  nodes: NodeSummary[];
  onSelect: (nodeId: string) => void;
}) {
  return (
    <div className="detail-group">
      <h4>{title}</h4>
      {nodes.length === 0 ? (
        <p className="empty-inline">None</p>
      ) : (
        <div className="node-link-list">
          {nodes.map((node) => (
            <button type="button" key={node.node_id} onClick={() => onSelect(node.node_id)}>
              <span>{node.canonical_name}</span>
              <small>{node.primary_type}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Relations({ title, relations }: { title: string; relations: RelationResult[] }) {
  return (
    <div className="detail-group relation-group">
      <h4>{title}</h4>
      {relations.length === 0 ? (
        <p className="empty-inline">None</p>
      ) : (
        relations.map((relation) => (
          <article className="relation-row" key={relation.relation_id}>
            <div className="relation-title">
              <strong>{relation.relation_type}</strong>
              <span>{formatConfidence(relation.confidence)}</span>
            </div>
            <p>{relation.from_canonical_name} <span aria-label="to">→</span> {relation.to_canonical_name}</p>
            <small>Scope: {relation.scope || "—"}</small>
          </article>
        ))
      )}
    </div>
  );
}

function OverviewTab({ detail, onSelect }: { detail: NodeDetail; onSelect: (nodeId: string) => void }) {
  return (
    <div className="tab-content overview-tab">
      <div className="node-identity">
        <span className="type-badge">{detail.primary_type}</span>
        <span className="status-badge">{detail.status}</span>
        <h3>{detail.canonical_name}</h3>
        <p>{detail.description || "No description recorded."}</p>
        <code>{detail.node_id}</code>
      </div>

      <div className="detail-group">
        <h4>Aliases</h4>
        {detail.aliases.length === 0 ? (
          <p className="empty-inline">None</p>
        ) : (
          <div className="alias-list">
            {detail.aliases.map((alias) => <span key={alias}>{alias}</span>)}
          </div>
        )}
      </div>

      <div className="hierarchy-grid">
        <NodeLinks title="Parents" nodes={detail.parents} onSelect={onSelect} />
        <NodeLinks title="Children" nodes={detail.children} onSelect={onSelect} />
      </div>
      <Relations title="Incoming Relations" relations={detail.incoming_relations} />
      <Relations title="Outgoing Relations" relations={detail.outgoing_relations} />
    </div>
  );
}

function ClaimsTab({
  claims,
  onOpenSource,
}: {
  claims: ClaimResult[];
  onOpenSource: (sourceId: string) => void;
}) {
  if (claims.length === 0) {
    return <div className="tab-empty">No Claims are linked to this Node.</div>;
  }
  return (
    <div className="tab-content card-list">
      {claims.map((claim) => (
        <article className="claim-card" key={claim.claim_id}>
          <div className="card-badges">
            <span>{claim.link_role === "subject" ? "Subject" : claim.link_role === "context" ? "Context" : "Related"}</span>
            <span>{claim.nature}</span>
            <span>{claim.status}</span>
            <span>{claim.novelty_level}</span>
          </div>
          <h3>{claim.statement}</h3>
          <dl className="metadata-grid">
            <div><dt>Fact time</dt><dd>{claim.fact_time || "—"}</dd></div>
            <div><dt>Published</dt><dd>{claim.publication_time || "—"}</dd></div>
            <div><dt>Confidence</dt><dd>{formatConfidence(claim.confidence)}</dd></div>
            <div><dt>Attributed to</dt><dd>{claim.attributed_to || "—"}</dd></div>
          </dl>
          <div className="evidence-block">
            <span>Evidence</span>
            <blockquote>{claim.evidence_excerpt || "No evidence excerpt recorded."}</blockquote>
            {claim.evidence_pointer && <small>{claim.evidence_pointer}</small>}
          </div>
          <button type="button" className="source-summary" onClick={() => onOpenSource(claim.source_id)}>
            <strong>{claim.source.title}</strong>
            <span>{[claim.source.organization, claim.source.publication_time, `Rank ${claim.source.source_rank}`].filter(Boolean).join(" · ")}</span>
          </button>
          <code>{claim.claim_id}</code>
        </article>
      ))}
    </div>
  );
}

function SourcesTab({
  sources,
  onOpenSource,
}: {
  sources: NodeSource[];
  onOpenSource: (sourceId: string) => void;
}) {
  if (sources.length === 0) {
    return <div className="tab-empty">No Sources are linked to this Node.</div>;
  }
  return (
    <div className="tab-content card-list">
      {sources.map((source) => (
        <article className="source-card" data-testid="source-card" key={source.source_id}>
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
          </dl>
          <div className="provenance-list">
            <h4>Why this Source is linked</h4>
            {source.provenance.map((provenance, index) => (
              <div className="provenance-entry" key={`${provenance.origin_path}-${provenance.claim_id ?? index}`}>
                <strong>{provenance.origin_path === "direct" ? "Direct node link" : "Via Claim"}</strong>
                <span>Role: {provenance.role}</span>
                {provenance.origin_path === "direct" && <span>Origin: {provenance.link_origin}</span>}
                {provenance.claim_id && <code>{provenance.claim_id}</code>}
                {provenance.evidence_excerpt && <blockquote>{provenance.evidence_excerpt}</blockquote>}
              </div>
            ))}
          </div>
          <div className="source-card-footer">
            <code>{source.source_id}</code>
            <button type="button" onClick={() => onOpenSource(source.source_id)}>Open Source</button>
          </div>
        </article>
      ))}
    </div>
  );
}

const tabs: Array<{ id: DetailTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "view", label: "View" },
  { id: "research", label: "Research" },
  { id: "claims", label: "Claims" },
  { id: "sources", label: "Sources" },
];

export function NodeDetailPanel(props: NodeDetailPanelProps) {
  const {
    selectedNodeId,
    detail,
    claims,
    sources,
    currentView,
    researchQuestion,
    knowledgeGaps,
    activeTab,
    loading,
    knowledgeLoading,
    error,
    knowledgeErrors,
    selectedSourceId,
    sourceDetail,
    sourceLoading,
    sourceError,
    onTabChange,
    onSelect,
    onOpenSource,
    onCloseSource,
  } = props;

  if (selectedSourceId) {
    return (
      <SourceDetailPanel
        sourceId={selectedSourceId}
        source={sourceDetail}
        loading={sourceLoading}
        error={sourceError}
        onBack={onCloseSource}
        onSelectNode={onSelect}
      />
    );
  }

  return (
    <section className="detail-panel" aria-labelledby="detail-heading">
      <div className="panel-heading detail-heading-row">
        <div>
          <p className="eyebrow">Canonical knowledge</p>
          <h2 id="detail-heading">Node Detail</h2>
        </div>
        {detail && <span className="detail-type">{detail.primary_type}</span>}
      </div>

      {!selectedNodeId && (
        <div className="detail-empty">
          <span aria-hidden="true">▤</span>
          <p>Select a node to inspect its knowledge.</p>
        </div>
      )}
      {selectedNodeId && loading && !detail && <div className="detail-empty"><p>Loading Node…</p></div>}
      {selectedNodeId && error && !detail && <div className="detail-empty is-error" role="alert"><p>{error}</p></div>}

      {detail && (
        <>
          <div className="tabs" role="tablist" aria-label="Node detail sections">
            {tabs.map((tab) => (
              <button
                type="button"
                role="tab"
                id={`tab-${tab.id}`}
                aria-controls={`panel-${tab.id}`}
                aria-selected={activeTab === tab.id}
                className={activeTab === tab.id ? "is-active" : ""}
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
              >
                {tab.label}
                {tab.id === "claims" && <span>{claims.length}</span>}
                {tab.id === "sources" && <span>{sources.length}</span>}
              </button>
            ))}
          </div>
          <div
            className="tab-panel"
            role="tabpanel"
            id={`panel-${activeTab}`}
            aria-labelledby={`tab-${activeTab}`}
          >
            {error && <div className="inline-error" role="alert">{error}</div>}
            {activeTab === "overview" && <OverviewTab detail={detail} onSelect={onSelect} />}
            {activeTab === "view" && (
              <ViewTab
                currentView={currentView}
                primaryType={detail.primary_type}
                loading={knowledgeLoading}
                error={knowledgeErrors.view}
                onOpenSource={onOpenSource}
              />
            )}
            {activeTab === "research" && (
              <ResearchTab
                researchQuestion={researchQuestion}
                knowledgeGaps={knowledgeGaps}
                loading={knowledgeLoading}
                researchError={knowledgeErrors.research}
                gapsError={knowledgeErrors.gaps}
              />
            )}
            {activeTab === "claims" && (
              knowledgeErrors.claims
                ? <div className="tab-empty is-error" role="alert">{knowledgeErrors.claims}</div>
                : knowledgeLoading && claims.length === 0
                  ? <div className="tab-empty">Loading Claims…</div>
                  : <ClaimsTab claims={claims} onOpenSource={onOpenSource} />
            )}
            {activeTab === "sources" && (
              knowledgeErrors.sources
                ? <div className="tab-empty is-error" role="alert">{knowledgeErrors.sources}</div>
                : knowledgeLoading && sources.length === 0
                  ? <div className="tab-empty">Loading Sources…</div>
                  : <SourcesTab sources={sources} onOpenSource={onOpenSource} />
            )}
          </div>
        </>
      )}
    </section>
  );
}
