import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCompanyMaterials, type CompanyMaterial, type CompanyMaterialsPage } from "../api/research";
import { CompanyMaterialsPanel } from "./CompanyMaterialsPanel";

vi.mock("../api/research", () => ({ getCompanyMaterials: vi.fn() }));

const material = (index: number, changes: Partial<CompanyMaterial> = {}): CompanyMaterial => ({
  material_id: `company-material:C1:S${index}`, source_id: `S${index}`, processing_run_id: `R${index}`,
  title: `Synthetic material ${index}`, title_basis: "operator_title", material_kind: "investor_qa",
  source_channel: "knowledge_community", material_trust_policy: "LOW_TRUST_CLUE_ONLY",
  material_date: `2026-09-${String(index).padStart(2, "0")}`, material_date_basis: "operator_supplied",
  lifecycle: "qualified_unapplied", state: "QUALIFIED", private: true, canonical: false,
  association_basis: "company_material_intent", review_status: "SEALED", attribution_status: "SEALED",
  qualification_status: "QUALIFIED", canonical_source_id: null, claim_count: null,
  linked_node_count: null, linked_nodes: null, current_view_impact_candidate_count: null,
  uploaded_at: "2026-09-22", publication_time: null, ingested_at: null, updated_at: "2026-09-22",
  packet_artifact_id: `A${index}`, company_material_intent_sha256: "a".repeat(64), ...changes,
});

const page = (materials: CompanyMaterial[]): CompanyMaterialsPage => ({
  company: { node_id: "C1", canonical_name: "Synthetic Company", primary_type: "Company", status: "active" },
  materials, counts: { total: materials.length, private: materials.filter(item => !item.canonical).length,
    canonical: materials.filter(item => item.canonical).length }, snapshot_id: "a".repeat(64), next_cursor: null,
});

describe("Company Materials panel", () => {
  beforeEach(() => vi.resetAllMocks());

  it("shows the empty Company state and upload route", async () => {
    vi.mocked(getCompanyMaterials).mockResolvedValue(page([]));
    render(<CompanyMaterialsPanel companyId="C1" navigate={vi.fn()} />);
    expect(await screen.findByText("No company materials recorded.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add latest material" })).toHaveAttribute("href", "/source-operations?company=C1");
  });

  it("shows five latest materials then expands, with private trust and review links", async () => {
    vi.mocked(getCompanyMaterials).mockResolvedValue(page(Array.from({ length: 6 }, (_, i) => material(i + 1))));
    render(<CompanyMaterialsPanel companyId="C1" navigate={vi.fn()} />);
    expect(await screen.findByText("Synthetic material 1")).toBeInTheDocument();
    expect(screen.queryByText("Synthetic material 6")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show all 6 materials" }));
    expect(screen.getByText("Synthetic material 6")).toBeInTheDocument();
    expect(screen.getAllByText(/Clue source/)).toHaveLength(6);
    expect(screen.getAllByRole("link", { name: "Open Operations" })[0]).toHaveAttribute("href", "/source-operations/S1?company=C1");
    expect(screen.getAllByRole("link", { name: "Open Review Workbench" })[0]).toHaveAttribute("href", "/?surface=review&artifact=A1");
  });

  it("opens canonical Source and explicitly linked affected Node", async () => {
    const navigate = vi.fn();
    vi.mocked(getCompanyMaterials).mockResolvedValue(page([material(1, {
      title: "Canonical report", title_basis: "canonical_source", lifecycle: "activated",
      state: "ACTIVATED", canonical: true, canonical_source_id: "S1", claim_count: 2,
      linked_node_count: 2, linked_nodes: [{ node_id: "C1", canonical_name: "Synthetic Company", primary_type: "Company", roles: "subject" },
        { node_id: "P1", canonical_name: "Synthetic Product", primary_type: "Product", roles: "context" }],
      current_view_impact_candidate_count: 1, association_basis: "claim_node_link",
    })]));
    render(<CompanyMaterialsPanel companyId="C1" navigate={navigate} />);
    const panel = await screen.findByRole("region", { name: "Latest Materials" });
    expect(within(panel).getByText(/Potential Current View impact: 1/)).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole("button", { name: "Synthetic Product · Product" }));
    expect(navigate).toHaveBeenCalledWith({ kind: "node", id: "P1" });
    fireEvent.click(within(panel).getByRole("button", { name: "Open Source" }));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith({ kind: "source", id: "S1" }));
  });
});
