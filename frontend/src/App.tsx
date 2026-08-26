import { useCallback, useEffect, useRef, useState } from "react";

import { getClaims, getHealth, getNeighbors, getNode, getSources, getStats } from "./api/client";
import type { ClaimResult, NeighborGraph, NodeDetail, NodeSource, StatsResponse } from "./api/types";
import { GraphPanel } from "./components/GraphPanel";
import { NodeDetailPanel, type DetailTab } from "./components/NodeDetailPanel";
import { SearchPanel } from "./components/SearchPanel";

export default function App() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [graph, setGraph] = useState<NeighborGraph | null>(null);
  const [claims, setClaims] = useState<ClaimResult[]>([]);
  const [sources, setSources] = useState<NodeSource[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [selectionLoading, setSelectionLoading] = useState(false);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const statusController = useRef<AbortController | null>(null);
  const selectionController = useRef<AbortController | null>(null);

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
    const controller = new AbortController();
    selectionController.current = controller;

    setSelectedNodeId(nodeId);
    setDetail(null);
    setGraph(null);
    setClaims([]);
    setSources([]);
    setActiveTab("overview");
    setSelectionLoading(true);
    setSelectionError(null);

    const url = new URL(window.location.href);
    url.searchParams.set("node", nodeId);
    window.history.replaceState(null, "", url);

    Promise.all([
      getNode(nodeId, controller.signal),
      getNeighbors(nodeId, controller.signal),
      getClaims(nodeId, controller.signal),
      getSources(nodeId, controller.signal),
    ])
      .then(([nodeDetail, neighborGraph, nodeClaims, nodeSources]) => {
        if (controller.signal.aborted) return;
        setDetail(nodeDetail);
        setGraph(neighborGraph);
        setClaims(nodeClaims);
        setSources(nodeSources);
        setApiOnline(true);
      })
      .catch((error) => {
        if ((error as Error).name !== "AbortError") {
          setSelectionError("Unable to load this Node from the local Knowledge API.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSelectionLoading(false);
      });
  }, []);

  useEffect(() => {
    void loadStatus();
    return () => statusController.current?.abort();
  }, [loadStatus]);

  useEffect(() => {
    const nodeId = new URLSearchParams(window.location.search).get("node");
    if (nodeId) selectNode(nodeId);
    return () => selectionController.current?.abort();
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
          error={selectionError}
          onSelect={selectNode}
        />
        <NodeDetailPanel
          selectedNodeId={selectedNodeId}
          detail={detail}
          claims={claims}
          sources={sources}
          activeTab={activeTab}
          loading={selectionLoading}
          error={selectionError}
          onTabChange={setActiveTab}
          onSelect={selectNode}
        />
      </main>
    </div>
  );
}
