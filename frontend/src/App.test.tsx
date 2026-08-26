import { StrictMode } from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getClaims, getHealth, getNeighbors, getNode, getSources, getStats } from "./api/client";
import App from "./App";

vi.mock("./api/client", () => ({
  getClaims: vi.fn(),
  getHealth: vi.fn(),
  getNeighbors: vi.fn(),
  getNode: vi.fn(),
  getSources: vi.fn(),
  getStats: vi.fn(),
  searchNodes: vi.fn(),
}));

describe("App error boundary", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    const unavailable = new TypeError("Failed to fetch");
    vi.mocked(getHealth).mockRejectedValue(unavailable);
    vi.mocked(getStats).mockRejectedValue(unavailable);
    vi.mocked(getNode).mockRejectedValue(unavailable);
    vi.mocked(getNeighbors).mockRejectedValue(unavailable);
    vi.mocked(getClaims).mockRejectedValue(unavailable);
    vi.mocked(getSources).mockRejectedValue(unavailable);
  });

  it("renders a useful unavailable state instead of a white screen", async () => {
    render(<App />);
    expect(await screen.findByText("Knowledge API unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Start the local pro_a API and retry.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.getByText("Search for a node to start exploring.")).toBeInTheDocument();
  });

  it("restores a selected node from the URL in StrictMode", async () => {
    window.history.replaceState(null, "", "/?node=NODE_EML");
    vi.mocked(getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(getStats).mockResolvedValue({
      active_node_count: 1,
      alias_count: 1,
      current_relation_count: 0,
      current_part_of_count: 0,
      source_count: 0,
      claim_count: 0,
      current_view_count: 0,
      open_knowledge_gap_count: 0,
      open_research_question_count: 0,
    });
    vi.mocked(getNode).mockResolvedValue({
      node_id: "NODE_EML",
      canonical_name: "EML",
      primary_type: "Product",
      description: "高速光芯片技术",
      status: "active",
      aliases: ["Electro-Absorption Modulated Laser"],
      parents: [],
      children: [],
      incoming_relations: [],
      outgoing_relations: [],
    });
    vi.mocked(getNeighbors).mockResolvedValue({
      center: { node_id: "NODE_EML", canonical_name: "EML", primary_type: "Product" },
      nodes: [{ node_id: "NODE_EML", canonical_name: "EML", primary_type: "Product" }],
      edges: [],
    });
    vi.mocked(getClaims).mockResolvedValue([]);
    vi.mocked(getSources).mockResolvedValue([]);

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    );

    expect(await screen.findByRole("heading", { name: "EML" })).toBeInTheDocument();
    expect(getNode).toHaveBeenCalledTimes(2);
  });
});
