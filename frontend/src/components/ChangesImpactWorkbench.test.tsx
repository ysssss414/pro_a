import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getImpactChanges,
  getSession,
  saveImpactAttention,
  type DirectImpactItem,
  type ImpactChangesResult,
} from "../api/workbench";
import { ChangesImpactWorkbench } from "./ChangesImpactWorkbench";

vi.mock("../api/workbench", async (original) => {
  const actual = await original<typeof import("../api/workbench")>();
  return { ...actual, getImpactChanges: vi.fn(), getSession: vi.fn(), saveImpactAttention: vi.fn() };
});

function item(overrides: Partial<DirectImpactItem>): DirectImpactItem {
  return {
    impact_id: "IMP.one." + "a".repeat(64), impact_type: "DIRECT_NODE",
    origin_type: "SOURCE", origin_id: "SRC_CHANGE", target_type: "NODE", target_id: "NODE_COMPANY",
    path_steps: [
      { object_type: "SOURCE", object_id: "SRC_CHANGE", label: "Recorded change", status: "stored" },
      { object_type: "CLAIM", object_id: "CLM_CHANGE", label: "Recorded operating change", status: "current" },
      { object_type: "NODE", object_id: "NODE_COMPANY", label: "Recorded Company", status: "active" },
    ],
    relationship_types: ["SOURCE_HAS_CLAIM", "EXPLICIT_ATTRIBUTION"], attribution_role: "subject",
    official_or_staged: "RECORDED", reason_code: "CLAIM_ATTRIBUTED_TO_NODE",
    evidence_refs: [{ claim_id: "CLM_CHANGE", source_id: "SRC_CHANGE" }],
    temporal_status: { effective_date: "2026-04-01", temporal_relation: "recorded_claim_status" },
    current_status: "active", is_current_impact: true, snapshot_id: "1".repeat(64), attention_state: null,
    ...overrides,
  };
}

const nodeItem = item({});
const officialItem = item({
  impact_id: "IMP.one." + "b".repeat(64), impact_type: "OFFICIAL_VIEW", target_type: "VIEW", target_id: "VIEW_CURRENT",
  path_steps: [nodeItem.path_steps[0], nodeItem.path_steps[1], nodeItem.path_steps[2],
    { object_type: "VIEW", object_id: "VIEW_CURRENT", label: "v_20260401", status: "official" }],
  relationship_types: ["SOURCE_HAS_CLAIM", "EXPLICIT_ATTRIBUTION", "NODE_CURRENT_OFFICIAL_VIEW"],
  official_or_staged: "OFFICIAL", reason_code: "NODE_HAS_OFFICIAL_VIEW", current_status: "official",
});
const stagedItem = item({
  impact_id: "IMP.one." + "c".repeat(64), impact_type: "DRAFT_VIEW", target_type: "VIEW_DRAFT", target_id: "DRAFT_PRODUCT",
  path_steps: [nodeItem.path_steps[0], nodeItem.path_steps[1],
    { object_type: "VIEW_DRAFT", object_id: "DRAFT_PRODUCT", label: "revision 1", status: "DRAFT" }],
  relationship_types: ["SOURCE_HAS_CLAIM", "EXPLICIT_DRAFT_EVIDENCE"], attribution_role: "context",
  official_or_staged: "STAGED", reason_code: "STAGED_VIEW_DEPENDENCY", current_status: "DRAFT",
});
const contradictionItem = item({
  impact_id: "IMP.one." + "d".repeat(64), impact_type: "CONTRADICTION", target_type: "CLAIM", target_id: "CLM_OLD",
  path_steps: [nodeItem.path_steps[0], nodeItem.path_steps[1],
    { object_type: "CLAIM_RELATION", object_id: "REL_CONTRA", label: "contradicts", status: "recorded" },
    { object_type: "CLAIM", object_id: "CLM_OLD", label: "Older recorded Claim", status: "historical" }],
  relationship_types: ["SOURCE_HAS_CLAIM", "CONTRADICTS"], attribution_role: null,
  official_or_staged: "RECORDED", reason_code: "RECORDED_CONTRADICTION", current_status: "historical",
});
const categoricalItem = item({
  impact_id: "IMP.one." + "e".repeat(64), impact_type: "RELATION_EVIDENCE", target_type: "RELATION", target_id: "REL_CATEGORY",
  path_steps: [nodeItem.path_steps[0], nodeItem.path_steps[1],
    { object_type: "RELATION", object_id: "REL_CATEGORY", label: "related_to", status: "categorical" }],
  relationship_types: ["RELATION_EVIDENCE_SUPPORTS", "RELATED_TO"], attribution_role: null,
  official_or_staged: "CATEGORICAL", reason_code: "RECORDED_RELATION_EVIDENCE",
  current_status: "categorical", is_current_impact: false,
});

const result: ImpactChangesResult = {
  snapshot: { snapshot_id: "f".repeat(64), knowledge_sha256: "a".repeat(64), workbench_projection_sha256: "b".repeat(64),
    cache: "NONE", consistency: "TRANSACTIONAL_READ_SNAPSHOT", query_count: 9 },
  changes: [{ source: { source_id: "SRC_CHANGE", title: "Recorded change", publication_time: "2026-04-01",
    ingested_at: "2026-04-02", status: "stored", source_type: "SYNTHETIC_TEXT", source_rank: "A" },
    evidence_date: "2026-04-01", current_status: "stored", claim_count: 3,
    claims: [{ claim_id: "CLM_CHANGE", statement: "Recorded operating change", status: "current", fact_time: "", publication_time: "2026-04-01" }],
    snapshot_id: "1".repeat(64), items: [nodeItem, officialItem, stagedItem, contradictionItem, categoricalItem] }],
  items: [nodeItem, officialItem, stagedItem, contradictionItem, categoricalItem], limit: 50, offset: 0,
};

describe("Changes & Impact Workbench", () => {
  beforeEach(() => {
    vi.mocked(getImpactChanges).mockResolvedValue(result);
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "DEMO", csrf_token: "csrf" });
    vi.mocked(saveImpactAttention).mockReset();
    Object.defineProperty(globalThis.crypto, "randomUUID", { configurable: true, value: vi.fn(() => "00000000-0000-0000-0000-000000000099") });
  });

  it("presents one coherent non-graph surface with exact direct paths", async () => {
    const onOpen = vi.fn();
    render(<ChangesImpactWorkbench onOpenOfficialView={onOpen} />);
    expect(await screen.findByRole("heading", { name: "Changes & Impact" })).toBeInTheDocument();
    for (const heading of ["Changes", "Directly Affected", "Official Views", "Staged View Work", "Evidence Paths", "Contradictions / Temporal", "Attention State"])
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getAllByText("Attribution: subject").length).toBeGreaterThan(0);
    expect(screen.getByText("Attribution: context")).toBeInTheDocument();
    expect(screen.getByText(/Only directly recorded evidence paths/)).toBeInTheDocument();
    expect(screen.queryByText(/Synthetic Cooccurring Alias/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Bullish|Bearish|Buy|Sell/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open official View" }));
    expect(onOpen).toHaveBeenCalledWith("NODE_COMPANY", "VIEW_CURRENT");
  });

  it("labels contradiction and categorical provenance without claiming confirmation", async () => {
    render(<ChangesImpactWorkbench onOpenOfficialView={vi.fn()} />);
    await screen.findByRole("heading", { name: "Contradictions / Temporal" });
    const section = screen.getByRole("heading", { name: "Contradictions / Temporal" }).closest("section")!;
    expect(within(section).getByText("Recorded contradiction")).toBeInTheDocument();
    expect(within(section).getByText("Provenance only · not current Impact")).toBeInTheDocument();
    expect(screen.queryByText(/confirmed true/i)).not.toBeInTheDocument();
  });

  it("records an exact Workbench-only attention outcome", async () => {
    vi.mocked(saveImpactAttention).mockResolvedValue({ attention_state: {
      outcome: "NO_CHANGE", revision: 1, reviewer: "Operator One", actor: "operator",
      reason: "Official View remains adequate", updated_at: "2026-04-03", status: "CURRENT",
      snapshot_id: nodeItem.snapshot_id,
    }, canonical_write: false, production_authorized: false });
    render(<ChangesImpactWorkbench onOpenOfficialView={vi.fn()} />);
    await screen.findByRole("heading", { name: "Attention State" });
    fireEvent.click(screen.getByRole("radio", { name: "No Change" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Reviewer" }), { target: { value: "Operator One" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Reason" }), { target: { value: "Official View remains adequate" } });
    fireEvent.click(screen.getByRole("button", { name: "Save attention outcome" }));
    await screen.findByText("Attention outcome saved in Workbench state.");
    expect(saveImpactAttention).toHaveBeenCalledWith(nodeItem.impact_id, expect.objectContaining({
      snapshot_id: nodeItem.snapshot_id, expected_revision: 0, outcome: "NO_CHANGE", reviewer: "Operator One",
    }), "csrf", expect.any(AbortSignal));
    await waitFor(() => expect(screen.getByText("Attention: No Change · CURRENT")).toBeInTheDocument());
  });
});
