import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getSession, getViewWorkbench, qualifyViewDraft, reconcileViewReceipt, saveViewDraft,
  validateViewDraft, type CurrentViewWorkbenchState,
} from "../api/workbench";
import { CurrentViewWorkbench } from "./CurrentViewWorkbench";

vi.mock("../api/workbench", () => ({
  getSession: vi.fn(), getViewWorkbench: vi.fn(), qualifyViewDraft: vi.fn(),
  reconcileViewReceipt: vi.fn(), saveViewDraft: vi.fn(), validateViewDraft: vi.fn(),
}));

const content = {
  one_line_conclusion: "Synthetic Company official conclusion",
  core_logic: ["Synthetic Company logic [CLM_PRIMARY]"],
  key_facts: ["Synthetic Company fact [CLM_PRIMARY]"],
  core_disagreements: ["Synthetic Company uncertainty"],
  assumptions_to_verify: ["Synthetic Company assumption"],
  investment_implication: "Synthetic Company implication",
  major_risks: ["Synthetic Company risk [CLM_PRIMARY]"],
  knowledge_gaps: ["Synthetic Company 缺少 evidence"],
  key_watch_items: ["需跟踪 Synthetic Company"],
  recent_change: "Synthetic Company evidence changed",
  evidence_claim_ids: ["CLM_PRIMARY"], type_specific: {},
};

const official = {
  view_id: "VIEW_CURRENT", node_id: "NODE_COMPANY", version: "v_20260901", status: "official",
  change_level: "minor", previous_view_id: "VIEW_PRIOR", content_md: "Synthetic",
  content_json: content, trigger_source_id: "SRC_PRIMARY", trigger_claim_ids: ["CLM_PRIMARY"],
  revision_date: "20260901", revision_seq: 0, accepted_proposal_id: "", created_at: "2026-09-01",
  confirmed_at: "2026-09-01",
};

const primary = {
  claim_id: "CLM_PRIMARY", statement: "Synthetic Company fact", nature: "fact", status: "current",
  confidence: 0.9, role: "subject" as const, scope: "synthetic", attributed_to: "",
  evidence_excerpt: "Synthetic Company evidence", evidence_pointer: "synthetic:1",
  source_locator: { status: "resolved", locator: "TEXT" },
  source: { source_id: "SRC_PRIMARY", title: "Primary source", publication_time: "2026-08-31",
    source_rank: "A", source_type: "SYNTHETIC_TEXT", organization: "Synthetic", sha256: "a".repeat(64) },
  business_date: "2026-08-30", freshness_basis: "claim_fact_time", primary_eligible: true,
};

const contextual = {
  ...primary, claim_id: "CLM_CONTEXT", statement: "Synthetic context", role: "context" as const,
  source: { ...primary.source, source_id: "SRC_CONTEXT", title: "Context source", sha256: "b".repeat(64) },
  business_date: null, freshness_basis: "unknown", primary_eligible: false,
};

function workbench(overrides: Partial<CurrentViewWorkbenchState> = {}): CurrentViewWorkbenchState {
  return {
    node: { node_id: "NODE_COMPANY", canonical_name: "Synthetic Company", primary_type: "Company", status: "active" },
    selection_rule: "revision_date DESC,revision_seq DESC,view_id DESC", official,
    previous_official: { ...official, view_id: "VIEW_PRIOR", version: "v_20260801", previous_view_id: null },
    history: [official, { ...official, view_id: "VIEW_PRIOR", version: "v_20260801", previous_view_id: null }],
    baseline_views: [{ ...official, view_id: "BASELINE_SYNTHETIC", version: "baseline_BASELINE_SYNTHETIC", status: "baseline" }],
    history_labels: [{ view_id: "VIEW_CURRENT", state: "OFFICIAL" }, { view_id: "VIEW_PRIOR", state: "PRIOR_OFFICIAL" }],
    official_comparison: { has_changes: true, scalar_changes: [{ field: "one_line_conclusion", changed: true }] },
    official_evidence: [{ ...primary, resolved: true, officially_referenced: true, evidence_class: "PRIMARY" },
      { ...contextual, resolved: true, officially_referenced: false, evidence_class: "CONTEXT_ONLY" }],
    available_evidence: [primary, contextual],
    freshness: [{ claim_id: "CLM_PRIMARY", business_date: "2026-08-30", basis: "claim_fact_time" },
      { claim_id: "CLM_CONTEXT", business_date: null, basis: "unknown" }],
    uncertainty: { core_disagreements: ["Synthetic Company uncertainty"], assumptions_to_verify: ["Synthetic assumption"], knowledge_gaps: ["Missing evidence"], review_needed_claims: [] },
    basis_sha256: "c".repeat(64), draft: null, activation_packages: [], activation_receipts: [],
    capabilities: { initial_supported: false, update_supported: true, browser_activation: false, canonical_write: false },
    ...overrides,
  } as CurrentViewWorkbenchState;
}

function draft(status: "DRAFT" | "VALIDATED" | "STALE" = "DRAFT") {
  return { draft_id: "VIEWDRAFT_1", revision: status === "VALIDATED" ? 2 : 1, reviewer: "Synthetic Reviewer",
    status, basis_sha256: "c".repeat(64), updated_at: "2026-09-02", mode: "UPDATE" as const,
    expected_official_view_id: "VIEW_CURRENT", content: { ...content, one_line_conclusion: "Synthetic Company draft" },
    primary_claim_ids: ["CLM_PRIMARY"], context_claim_ids: ["CLM_CONTEXT"], change_level: "minor" as const,
    quality_validation: status === "VALIDATED" ? { status: "PASS" } : null,
    audit: [{ revision: 1, action: "SAVE", reviewer: "Synthetic Reviewer", reason: "Synthetic", updated_at: "2026-09-02" }] };
}

describe("CurrentViewWorkbench", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "DEMO", csrf_token: "csrf" });
    vi.mocked(getViewWorkbench).mockResolvedValue(workbench());
    vi.mocked(saveViewDraft).mockResolvedValue({ draft_id: "VIEWDRAFT_1", revision: 1, status: "DRAFT", basis_sha256: "c".repeat(64) });
    vi.mocked(validateViewDraft).mockResolvedValue({ draft_id: "VIEWDRAFT_1", revision: 2, status: "VALIDATED", quality_validation: { status: "PASS" } });
  });

  it("separates official, prior, baseline and draft states while showing structured official semantics", async () => {
    render(<CurrentViewWorkbench nodeId="NODE_COMPANY" onOpenSource={vi.fn()} />);
    expect(await screen.findByText(/OFFICIAL: VIEW_CURRENT/)).toBeInTheDocument();
    expect(screen.getByText(/PRIOR: VIEW_PRIOR/)).toBeInTheDocument();
    expect(screen.getByText(/BASELINE: 1 excluded/)).toBeInTheDocument();
    expect(screen.getAllByText("Synthetic Company logic [CLM_PRIMARY]")).toHaveLength(2);
    expect(screen.getAllByText(/minor/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Synthetic Company evidence changed/).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 official primary citation/)).toBeInTheDocument();
  });

  it("shows primary/context roles, exact freshness basis and Source navigation", async () => {
    const onOpenSource = vi.fn(); const onOpenClaim = vi.fn();
    render(<CurrentViewWorkbench nodeId="NODE_COMPANY" onOpenSource={onOpenSource} onOpenClaim={onOpenClaim} />);
    expect(await screen.findByText(/Subject \/ primary eligible/)).toHaveTextContent("referenced by official View");
    expect(screen.getAllByText("Context only").length).toBeGreaterThan(0);
    expect(screen.getByText("2026-08-30")).toBeInTheDocument();
    expect(screen.getAllByText("unknown")).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: "Open Claim" })[0]);
    expect(onOpenClaim).toHaveBeenCalledWith("CLM_PRIMARY");
    fireEvent.click(screen.getAllByRole("button", { name: "Open Source" })[1]);
    expect(onOpenSource).toHaveBeenCalledWith("SRC_CONTEXT");
  });

  it("persists an explicit server draft with selected primary and context evidence", async () => {
    render(<CurrentViewWorkbench nodeId="NODE_COMPANY" onOpenSource={vi.fn()} />);
    await screen.findByText(/OFFICIAL: VIEW_CURRENT/);
    fireEvent.click(screen.getAllByRole("checkbox", { name: "Primary Evidence" })[0]);
    fireEvent.click(screen.getAllByRole("checkbox", { name: "Context only" })[1]);
    fireEvent.change(screen.getByLabelText("One-line conclusion"), { target: { value: "Synthetic Company edited" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft on server" }));
    await waitFor(() => expect(saveViewDraft).toHaveBeenCalledOnce());
    const body = vi.mocked(saveViewDraft).mock.calls[0][1] as Record<string, any>;
    expect(body.primary_claim_ids).toEqual(["CLM_PRIMARY"]); expect(body.context_claim_ids).toEqual(["CLM_CONTEXT"]);
    expect((body.content as Record<string, unknown>).one_line_conclusion).toBe("Synthetic Company edited");
    expect(body.expected_official_view_id).toBe("VIEW_CURRENT");
  });

  it("builds a bounded Product initial draft with the required structured type fields", async () => {
    const initial=workbench({
      node: { node_id: "NODE_PRODUCT", canonical_name: "Synthetic Product", primary_type: "Product", status: "active" },
      official: null, previous_official: null, history: [], history_labels: [], baseline_views: [], official_comparison: null,
      official_evidence: [], available_evidence: [{ ...primary, claim_id: "CLM_PRODUCT" }],
      capabilities: { initial_supported: true, update_supported: false, browser_activation: false, canonical_write: false },
    });
    vi.mocked(getViewWorkbench).mockResolvedValue(initial);
    render(<CurrentViewWorkbench nodeId="NODE_PRODUCT" onOpenSource={vi.fn()} />);
    await screen.findByText(/OFFICIAL: NO_EXISTING_VIEW/);
    fireEvent.click(screen.getByRole("checkbox", { name: "Primary Evidence" }));
    fireEvent.click(screen.getByRole("button", { name: "Save draft on server" }));
    await waitFor(() => expect(saveViewDraft).toHaveBeenCalledOnce());
    const body = vi.mocked(saveViewDraft).mock.calls[0][1] as Record<string, any>;
    expect(body.mode).toBe("INITIAL"); expect(body.change_level).toBe("initial");
    expect(Object.keys((body.content as Record<string, any>).type_specific).sort()).toEqual([
      "applications", "demand_drivers", "major_suppliers", "pricing", "product_evolution", "supply_capacity",
    ]);
  });

  it("blocks a stale draft from validation and qualification", async () => {
    vi.mocked(getViewWorkbench).mockResolvedValue(workbench({ draft: draft("STALE") }));
    render(<CurrentViewWorkbench nodeId="NODE_COMPANY" onOpenSource={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("BASELINE_STALE");
    expect(screen.getByRole("button", { name: "Validate existing quality contract" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Qualify for external operator" })).toBeDisabled();
  });

  it("validates and qualifies without exposing a browser activation action", async () => {
    vi.mocked(getViewWorkbench).mockResolvedValue(workbench({ draft: draft("VALIDATED") }));
    vi.mocked(qualifyViewDraft).mockResolvedValue({ object_id: "VIEWPACKAGE_1", adapter_version: "phase42-view-v1",
      production_authorized: false, predicted_diff: { table: "current_views", operation: "INSERT" },
      operator_action: "EXTERNAL_OPERATOR_REQUIRED" });
    render(<CurrentViewWorkbench nodeId="NODE_COMPANY" onOpenSource={vi.fn()} />);
    await screen.findByText(/DRAFT: VALIDATED r2/);
    fireEvent.click(screen.getByRole("button", { name: "Qualify for external operator" }));
    expect(await screen.findByRole("heading", { name: "READY_FOR_OPERATOR_ACTION" })).toBeInTheDocument();
    expect(screen.getByText(/Production authorized: false/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /activate|apply/i })).toBeNull();
  });

  it("shows broken official citations and reconciles only a registered receipt", async () => {
    vi.mocked(getViewWorkbench).mockResolvedValue(workbench({ official_evidence: [
      { claim_id: "CLM_MISSING", resolved: false, officially_referenced: true, evidence_class: "PRIMARY", error: "EVIDENCE_NOT_FOUND" },
    ] }));
    vi.mocked(reconcileViewReceipt).mockResolvedValue({ status: "VERIFIED", receipt_id: "VIEWEXECUTION_1",
      package_id: "VIEWPACKAGE_1", official_view_id: "VIEW_NEW" });
    render(<CurrentViewWorkbench nodeId="NODE_COMPANY" onOpenSource={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("EVIDENCE_NOT_FOUND");
    fireEvent.change(screen.getByLabelText("Registered activation receipt"), { target: { value: "VIEWEXECUTION_1" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify registered receipt" }));
    expect(await screen.findByText(/VERIFIED — official View VIEW_NEW/)).toBeInTheDocument();
    expect(reconcileViewReceipt).toHaveBeenCalledWith("NODE_COMPANY", "VIEWEXECUTION_1", "csrf", expect.any(AbortSignal));
  });

  it("fails closed for unsupported Node types", async () => {
    vi.mocked(getViewWorkbench).mockResolvedValue(workbench({
      node: { node_id: "NODE_TECH", canonical_name: "Synthetic Technology", primary_type: "Technology", status: "active" },
      official: null, previous_official: null, history: [], history_labels: [], baseline_views: [], official_comparison: null,
      capabilities: { initial_supported: false, update_supported: false, browser_activation: false, canonical_write: false },
    }));
    render(<CurrentViewWorkbench nodeId="NODE_TECH" onOpenSource={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("UNSUPPORTED_NODE_TYPE");
    expect(screen.queryByRole("button", { name: "Save draft on server" })).toBeNull();
  });
});
