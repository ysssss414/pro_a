import { useCallback, useEffect, useRef, useState } from "react";

import {
  getClaims,
  getCurrentView,
  getHealth,
  getKnowledgeGaps,
  getNeighbors,
  getNode,
  getResearchQuestion,
  getSourceDetail,
  getSources,
  getStats,
} from "./api/client";
import type {
  ClaimResult,
  CurrentViewResult,
  KnowledgeGapResult,
  NeighborGraph,
  NodeDetail,
  NodeSource,
  ResearchQuestionResult,
  SourceDetail,
  StatsResponse,
} from "./api/types";
import { GraphPanel } from "./components/GraphPanel";
import {
  NodeDetailPanel,
  type DetailTab,
  type KnowledgeErrors,
} from "./components/NodeDetailPanel";
import { SearchPanel } from "./components/SearchPanel";

function emptyKnowledgeErrors(): KnowledgeErrors {
  return { claims: null, sources: null, view: null, research: null, gaps: null };
}

export default function App() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [graph, setGraph] = useState<NeighborGraph | null>(null);
  const [claims, setClaims] = useState<ClaimResult[]>([]);
  const [sources, setSources] = useState<NodeSource[]>([]);
  const [currentView, setCurrentView] = useState<CurrentViewResult | null>(null);
  const [researchQuestion, setResearchQuestion] = useState<ResearchQuestionResult | null>(null);
  const [knowledgeGaps, setKnowledgeGaps] = useState<KnowledgeGapResult[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [selectionLoading, setSelectionLoading] = useState(false);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [knowledgeErrors, setKnowledgeErrors] = useState<KnowledgeErrors>(emptyKnowledgeErrors);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const statusController = useRef<AbortController | null>(null);
  const selectionController = useRef<AbortController | null>(null);
  const sourceController = useRef<AbortController | null>(null);

  const loadStatus = useCallback(async () => {
    statusController.current?.abort();
    const controller = new AbortController();
    statusController.current = controller;
    setStatusLoading(true);
    try {
      const [, currentStats] = await Promise.all([
        getHealth(controller.signal),
        getStats(controller.signal),
      ]);
      if (!controller.signal.aborted) {
        setApiOnline(true);
        setStats(currentStats);
      }
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        setApiOnline(false);
        setStats(null);
      }
    } finally {
      if (!controller.signal.aborted) setStatusLoading(false);
    }
  }, []);

  const selectNode = useCallback((nodeId: string) => {
    selectionController.current?.abort();
    sourceController.current?.abort();
    const controller = new AbortController();
    selectionController.current = controller;

    setSelectedNodeId(nodeId);
    setDetail(null);
    setGraph(null);
    setClaims([]);
    setSources([]);
    setCurrentView(null);
    setResearchQuestion(null);
    setKnowledgeGaps([]);
    setActiveTab("overview");
    setSelectionLoading(true);
    setKnowledgeLoading(true);
    setSelectionError(null);
    setGraphError(null);
    setKnowledgeErrors(emptyKnowledgeErrors());
    setSelectedSourceId(null);
    setSourceDetail(null);
    setSourceLoading(false);
    setSourceError(null);

    const url = new URL(window.location.href);
    url.searchParams.set("node", nodeId);
    window.history.replaceState(null, "", url);

    Promise.allSettled([
      getNode(nodeId, controller.signal),
      getNeighbors(nodeId, controller.signal),
    ])
      .then(([nodeResult, graphResult]) => {
        if (controller.signal.aborted) return;
        if (nodeResult.status === "fulfilled") {
          setDetail(nodeResult.value);
          setApiOnline(true);
        } else if ((nodeResult.reason as Error).name !== "AbortError") {
          setSelectionError("Unable to load this Node from the local Knowledge API.");
        }
        if (graphResult.status === "fulfilled") {
          setGraph(graphResult.value);
          setApiOnline(true);
        } else if ((graphResult.reason as Error).name !== "AbortError") {
          setGraphError("Unable to load this Node neighborhood.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSelectionLoading(false);
      });

    Promise.allSettled([
      getClaims(nodeId, controller.signal),
      getSources(nodeId, controller.signal),
      getCurrentView(nodeId, controller.signal),
      getResearchQuestion(nodeId, controller.signal),
      getKnowledgeGaps(nodeId, controller.signal),
    ])
      .then(([claimsResult, sourcesResult, viewResult, researchResult, gapsResult]) => {
        if (controller.signal.aborted) return;
        const errors = emptyKnowledgeErrors();

        if (claimsResult.status === "fulfilled") setClaims(claimsResult.value);
        else if ((claimsResult.reason as Error).name !== "AbortError") errors.claims = "Unable to load Claims.";

        if (sourcesResult.status === "fulfilled") setSources(sourcesResult.value);
        else if ((sourcesResult.reason as Error).name !== "AbortError") errors.sources = "Unable to load Sources.";

        if (viewResult.status === "fulfilled") setCurrentView(viewResult.value);
        else if ((viewResult.reason as Error).name !== "AbortError") errors.view = "Unable to load Current View.";

        if (researchResult.status === "fulfilled") setResearchQuestion(researchResult.value);
        else if ((researchResult.reason as Error).name !== "AbortError") errors.research = "Unable to load Research Question.";

        if (gapsResult.status === "fulfilled") setKnowledgeGaps(gapsResult.value);
        else if ((gapsResult.reason as Error).name !== "AbortError") errors.gaps = "Unable to load Knowledge Gaps.";

        setKnowledgeErrors(errors);
        if ([claimsResult, sourcesResult, viewResult, researchResult, gapsResult]
          .some((result) => result.status === "fulfilled")) setApiOnline(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setKnowledgeLoading(false);
      });
  }, []);

  const openSource = useCallback((sourceId: string) => {
    sourceController.current?.abort();
    const controller = new AbortController();
    sourceController.current = controller;
    setSelectedSourceId(sourceId);
    setSourceDetail(null);
    setSourceLoading(true);
    setSourceError(null);

    getSourceDetail(sourceId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setSourceDetail(result);
      })
      .catch((error) => {
        if ((error as Error).name !== "AbortError") {
          setSourceError("Unable to load Source detail.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSourceLoading(false);
      });
  }, []);

  const closeSource = useCallback(() => {
    sourceController.current?.abort();
    setSelectedSourceId(null);
    setSourceDetail(null);
    setSourceLoading(false);
    setSourceError(null);
  }, []);

  useEffect(() => {
    void loadStatus();
    return () => statusController.current?.abort();
  }, [loadStatus]);

  useEffect(() => {
    const nodeId = new URLSearchParams(window.location.search).get("node");
    if (nodeId) selectNode(nodeId);
    return () => {
      selectionController.current?.abort();
      sourceController.current?.abort();
    };
  }, [selectNode]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">p_a</span>
          <div>
            <strong>pro_a</strong>
            <span>Knowledge Explorer</span>
          </div>
        </div>
        <div className="header-status">
          {stats && (
            <div className="stats-summary" aria-label="Knowledge statistics">
              <strong>{stats.active_node_count}</strong> Nodes
              <span>·</span>
              <strong>{stats.current_relation_count}</strong> Current Relations
            </div>
          )}
          <div className={`api-status ${apiOnline === false ? "is-offline" : ""}`}>
            <span className="status-dot" aria-hidden="true" />
            {statusLoading && apiOnline === null
              ? "Checking API…"
              : apiOnline
                ? "API online"
                : "API unavailable"}
          </div>
        </div>
      </header>

      {apiOnline === false && (
        <div className="api-alert" role="alert">
          <div>
            <strong>Knowledge API unavailable.</strong>
            <span>Start the local pro_a API and retry.</span>
          </div>
          <button type="button" onClick={() => void loadStatus()} disabled={statusLoading}>
            {statusLoading ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}

      <main className="workspace-grid">
        <SearchPanel selectedNodeId={selectedNodeId} onSelect={selectNode} />
        <GraphPanel
          graph={graph}
          loading={selectionLoading}
          error={graphError}
          onSelect={selectNode}
        />
        <NodeDetailPanel
          selectedNodeId={selectedNodeId}
          detail={detail}
          claims={claims}
          sources={sources}
          currentView={currentView}
          researchQuestion={researchQuestion}
          knowledgeGaps={knowledgeGaps}
          activeTab={activeTab}
          loading={selectionLoading}
          knowledgeLoading={knowledgeLoading}
          error={selectionError}
          knowledgeErrors={knowledgeErrors}
          selectedSourceId={selectedSourceId}
          sourceDetail={sourceDetail}
          sourceLoading={sourceLoading}
          sourceError={sourceError}
          onTabChange={setActiveTab}
          onSelect={selectNode}
          onOpenSource={openSource}
          onCloseSource={closeSource}
        />
      </main>
    </div>
  );
}
