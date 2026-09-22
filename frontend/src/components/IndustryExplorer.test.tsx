import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getNodeDomainContext, getResearchDomains, getResearchDomainTree, getResearchNode, getResearchStructureMap, searchResearch,
  type NavigationNode, type NavigationTree,
} from "../api/research";
import { getSession } from "../api/workbench";
import { DomainHierarchyPanel, IndustryExplorer } from "./IndustryExplorer";

vi.mock("../api/research", () => ({
  getNodeDomainContext: vi.fn(), getResearchDomains: vi.fn(), getResearchDomainTree: vi.fn(),
  getResearchNode: vi.fn(), getResearchStructureMap: vi.fn(), searchResearch: vi.fn(),
}));
vi.mock("./SemanticStructureMap", () => ({ SemanticStructureMap: ({ mode, map, onMode, onDepth, onNode }:
  { mode: string; map: { selected_node_id: string | null } | null;
    onMode: (value: "focus") => void; onDepth: (value: number) => void; onNode: (id: string) => void }) =>
  <section aria-label="Semantic Structure Map"><span>Map mode: {mode}</span><span>Map Node: {map?.selected_node_id ?? "none"}</span>
    <button onClick={() => onMode("focus")}>Focus mode</button><button onClick={() => onDepth(3)}>Depth 3</button>
    <button onClick={() => onNode("B")}>Map select B</button></section> }));
vi.mock("../api/workbench", async (original) => {
  const actual = await original<typeof import("../api/workbench")>();
  return { ...actual, getSession: vi.fn() };
});
vi.mock("./CurrentViewWorkbench", () => ({
  CurrentViewWorkbench: ({ nodeId }: { nodeId: string }) => <div>Current View for {nodeId}</div>,
}));

const domains = [
  { domain_id: "ai_hardware", display_name: "AI Hardware", root_count: 1, visible_node_count: 2,
    max_tree_depth: 1, truncated: false, domain_pack_lifecycle: "PROPOSED", domain_pack_registered: false },
  { domain_id: "semiconductor", display_name: "Semiconductor", root_count: 1, visible_node_count: 1,
    max_tree_depth: 0, truncated: false, domain_pack_lifecycle: "PROPOSED", domain_pack_registered: false },
];

function node(id: string, name: string, depth: number, children: NavigationNode[] = []): NavigationNode {
  return { node_id: id, canonical_name: name, primary_type: "Product", status: "active", depth,
    child_count: children.length, has_children: children.length > 0, children };
}

const trees: Record<string, NavigationTree> = {
  ai_hardware: { domain_id: "ai_hardware", display_name: "AI Hardware", roots: [node("A", "Root A", 0, [node("A1", "Alpha", 1)])],
    visible_node_count: 2, max_tree_depth: 1, truncated: false, truncation_reasons: [], snapshot_id: "a" },
  semiconductor: { domain_id: "semiconductor", display_name: "Semiconductor", roots: [node("B", "Root B", 0)],
    visible_node_count: 1, max_tree_depth: 0, truncated: false, truncation_reasons: [], snapshot_id: "b" },
};

function researchNode(id: string) {
  return { node: { node_id: id, canonical_name: id === "A1" ? "Alpha" : "Root B", primary_type: "Product", status: "active", aliases: [] },
    current_view: null, impact: { items: [] }, coverage: { sources: 0 }, claims: { items: [], total: 0, limit: 20 },
    sources: [], relations: [], research_question: null, knowledge_gaps: [], notes: [] };
}

describe("Industry Explorer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState(null, "", "/industry");
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "DEMO", csrf_token: "csrf" });
    vi.mocked(getResearchDomains).mockResolvedValue({ domains });
    vi.mocked(getResearchDomainTree).mockImplementation(async (id) => trees[id]);
    vi.mocked(getResearchStructureMap).mockImplementation(async (id, mode, nodeId, depth) => ({
      domain_id: id, display_name: id, mode, selected_node_id: nodeId || null, depth,
      nodes: [], edges: [], stats: { node_count: 0, edge_count: 0 }, available_relation_types: [],
      truncated: false, truncation_reasons: [], snapshot_id: "map",
    }));
    vi.mocked(getResearchNode).mockImplementation(async (id) => researchNode(id));
    vi.mocked(getNodeDomainContext).mockImplementation(async (id) => ({ node_id: id,
      navigation_contexts: [{ domain_id: id === "B" ? "semiconductor" : "ai_hardware",
        display_name: id === "B" ? "Semiconductor" : "AI Hardware", root_node_id: id === "B" ? "B" : "A",
        path_from_root: id === "B" ? ["B"] : ["A", "A1"], depth: id === "B" ? 0 : 1 }],
      operational_domain_assignments: [] }));
    vi.mocked(searchResearch).mockResolvedValue({ query: "", results: [] });
  });

  it("selects a deterministic default, expands and collapses, then reuses Node research", async () => {
    render(<IndustryExplorer />);
    await waitFor(() => expect(window.location.search).toContain("domain=ai_hardware"));
    expect(await screen.findByRole("treeitem", { name: /Alpha/ }, { timeout: 5000 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Collapse Root A" }));
    expect(screen.queryByRole("treeitem", { name: /Alpha/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expand Root A" }));
    fireEvent.click(screen.getByRole("treeitem", { name: /Alpha/ }));
    expect(await screen.findByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.queryByText("Current View for A1")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Open Current View details / Workbench"));
    expect(await screen.findByText("Current View for A1")).toBeInTheDocument();
    expect(screen.getByRole("treeitem", { name: /Alpha/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("None recorded")).toBeInTheDocument();
    expect(window.location.search).toContain("node=A1");
  });

  it("restores deep links and switches domains through URL state", async () => {
    window.history.replaceState(null, "", "/industry?domain=semiconductor&node=B");
    render(<IndustryExplorer />);
    expect(await screen.findByRole("heading", { name: "Root B" })).toBeInTheDocument();
    expect(screen.getByLabelText("Domain")).toHaveValue("semiconductor");
    fireEvent.change(screen.getByLabelText("Domain"), { target: { value: "ai_hardware" } });
    await waitFor(() => expect(window.location.search).toBe("?domain=ai_hardware"));
    expect(screen.getByText("Select a node to inspect research.")).toBeInTheDocument();
    act(() => { window.history.replaceState(null, "", "/industry?domain=semiconductor&node=B"); window.dispatchEvent(new PopStateEvent("popstate")); });
    expect(await screen.findByRole("heading", { name: "Root B" })).toBeInTheDocument();
    expect(screen.getByLabelText("Domain")).toHaveValue("semiconductor");
  });

  it("opens searched nodes outside the tree without inventing a location", async () => {
    vi.mocked(searchResearch).mockResolvedValue({ query: "Outside", results: [{ object_type: "NODE", object_id: "OUT",
      label: "Outside", subtitle: "Product", status: "active" }] });
    render(<IndustryExplorer />);
    await screen.findByRole("treeitem", { name: /Root A/ });
    fireEvent.change(screen.getByLabelText("Find a canonical Node"), { target: { value: "Outside" } });
    fireEvent.click(await screen.findByRole("button", { name: /Outside/ }));
    expect(await screen.findByText("Node is outside the selected navigation tree.")).toBeInTheDocument();
    expect(screen.queryByRole("treeitem", { name: /Outside/ })).not.toBeInTheDocument();
  });

  it("keeps map mode, depth and canonical selection in URL navigation", async () => {
    render(<IndustryExplorer />);
    expect(await screen.findByText("Map mode: hierarchy")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("treeitem", { name: /Alpha/ }));
    expect(await screen.findByText("Map mode: relationship")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Focus mode" }));
    expect(window.location.search).toContain("map=focus");
    fireEvent.click(screen.getByRole("button", { name: "Depth 3" }));
    expect(window.location.search).toContain("depth=3");
    fireEvent.click(screen.getByRole("button", { name: "Map select B" }));
    expect(window.location.search).toContain("node=B");
    expect(await screen.findByText("Node is outside the selected navigation tree.")).toBeInTheDocument();
    act(() => { window.history.replaceState(null, "", "/industry?domain=ai_hardware&node=A1&map=focus&depth=2");
      window.dispatchEvent(new PopStateEvent("popstate")); });
    expect(await screen.findByText("Map Node: A1")).toBeInTheDocument();
    expect(window.location.search).toContain("depth=2");
  });

  it("never shows the previous Node summary while a new selection is loading", async () => {
    let resolveB!: (value: ReturnType<typeof researchNode>) => void;
    const slowB = new Promise<ReturnType<typeof researchNode>>((resolve) => { resolveB = resolve; });
    vi.mocked(getResearchNode).mockImplementation(async (id) => id === "B" ? slowB : researchNode(id));
    render(<IndustryExplorer />);
    fireEvent.click(await screen.findByRole("treeitem", { name: /Alpha/ }));
    expect(await screen.findByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Map select B" }));
    expect(screen.queryByRole("heading", { name: "Alpha" })).not.toBeInTheDocument();
    expect(screen.getByText("Loading Research Inspector…")).toHaveAttribute("role", "status");
    await act(async () => { resolveB(researchNode("B")); await slowB; });
    expect(await screen.findByRole("heading", { name: "Root B" })).toBeInTheDocument();
  });
});

it("announces empty, error and truncation states", () => {
  const props = { domains, domainId: "ai_hardware", selectedNodeId: "", onDomain: vi.fn(), onNode: vi.fn() };
  const { rerender } = render(<DomainHierarchyPanel {...props} tree={null} loading={true} error="" />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading canonical hierarchy");
  rerender(<DomainHierarchyPanel {...props} tree={null} loading={false} error="Backend unavailable" />);
  expect(screen.getByRole("alert")).toHaveTextContent("Backend unavailable");
  rerender(<DomainHierarchyPanel {...props} tree={{ ...trees.ai_hardware, roots: [], truncated: true,
    truncation_reasons: ["max_depth"] }} loading={false} error="" />);
  expect(screen.getByText("No active canonical roots are available.")).toBeInTheDocument();
  expect(screen.getByText(/Tree truncated: max_depth/)).toBeInTheDocument();
});
