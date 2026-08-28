import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getViewProposal, getViewProposals } from "./api/client";
import type { ViewProposalDetail } from "./api/types";
import { ViewProposalReview } from "./components/ViewProposalReview";

vi.mock("./api/client", () => ({ getViewProposal: vi.fn(), getViewProposals: vi.fn() }));

function proposal(decision: "minor" | "material" | "thesis" = "minor", id = "PROP_1"): ViewProposalDetail {
  return {
    proposal_id: id, status: "pending", node_id: "NODE_1", node_name: "MLCC", node_type: "Product",
    node_status: "active", node_resolved: true, decision, reason: "Explicit human review reason",
    trigger_source_id: "SRC_1", trigger_source: { source_id: "SRC_1", title: "Reviewed Source",
      publication_time: "2026-08-28", source_rank: "B", source_type: "md", origin_type: "secondary", resolved: true },
    previous_view_id: "VIEW_1", previous_version: "v_1", created_at: "2026-08-28", resolved_at: "",
    human_review_origin: true, canonical_alignment: "CURRENT",
    target_official_view: { view_id: "VIEW_1", node_id: "NODE_1", version: "v_1", revision_date: "20260828", change_level: "initial" },
    before_current_view: { one_line_conclusion: "Old exact conclusion" },
    proposed_current_view: { one_line_conclusion: "Human proposed conclusion" },
    diff: { scalar_changes: [{ field: "one_line_conclusion", changed: true, before: "Old exact conclusion", after: "Human proposed conclusion" }],
      list_changes: { key_facts: { added: ["New evidence fact"], removed: ["Prior evidence fact"], unchanged: [] } },
      type_specific_changes: { pricing: { kind: "list", status: "changed", added: ["New pricing observation"], removed: [], unchanged: [] } }, has_changes: true },
    human_review_handoff: { schema_version: "1" },
    thesis_break: { invalidated_core_assumption: "Human invalidated assumption", logic_chain_failure: "Human logic failure", conclusion_change: "Human conclusion change" },
    primary_evidence: [{ claim_id: "CLM_1", resolved: true, statement: "Primary Subject fact", status: "current", confidence: 0.8,
      source_id: "SRC_1", source_title: "Reviewed Source", source_rank: "B", nature: "data", attributed_to: "", scope: "行业", role: "subject" }],
    context_evidence: [{ claim_id: "CLM_2", resolved: true, statement: "Company Context fact", status: "current", confidence: 0.7,
      source_id: "SRC_1", source_title: "Reviewed Source", source_rank: "B", nature: "company_guidance", attributed_to: "Company", scope: "公司", role: "context" }],
    candidate_claims: [{ claim_id: "CLM_1", role: "subject" }, { claim_id: "CLM_2", role: "context" }],
  };
}

describe("read-only Human View Proposal review", () => {
  beforeEach(() => {
    vi.mocked(getViewProposals).mockResolvedValue([]);
    vi.mocked(getViewProposal).mockResolvedValue(proposal());
  });

  it("shows loading and a genuine empty queue", async () => {
    render(<ViewProposalReview onOpenSource={vi.fn()} />);
    expect(screen.getByText("Loading Human View Proposals…")).toBeInTheDocument();
    expect(await screen.findByText("No pending Human View Proposals")).toBeInTheDocument();
    expect(screen.queryByText("PENDING — NOT OFFICIAL CURRENT VIEW")).not.toBeInTheDocument();
  });

  it("shows list errors without manufacturing a Proposal", async () => {
    vi.mocked(getViewProposals).mockRejectedValue(new Error("offline"));
    render(<ViewProposalReview onOpenSource={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load Human View Proposals.");
    expect(screen.queryByText("No pending Human View Proposals")).not.toBeInTheDocument();
  });

  it.each(["minor", "material", "thesis"] as const)("reviews %s with diff, provenance and no mutation controls", async (decision) => {
    const row = proposal(decision);
    vi.mocked(getViewProposals).mockResolvedValue([row]);
    vi.mocked(getViewProposal).mockResolvedValue(row);
    const openSource = vi.fn();
    render(<ViewProposalReview onOpenSource={openSource} />);
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(`MLCC · ${decision.toUpperCase()}`) }));
    expect(await screen.findByText("PENDING — NOT OFFICIAL CURRENT VIEW")).toBeInTheDocument();
    const detail = screen.getByRole("region", { name: "Human View Proposal detail" });
    expect(within(detail).getByText("Explicit human review reason")).toBeInTheDocument();
    expect(within(detail).getByText("CURRENT")).toBeInTheDocument();
    expect(within(detail).getByText("Old exact conclusion")).toBeInTheDocument();
    expect(within(detail).getByText("Proposed", { exact: true })).toBeInTheDocument();
    expect(within(detail).getByText("New evidence fact")).toBeInTheDocument();
    expect(within(detail).getByText("Prior evidence fact")).toBeInTheDocument();
    expect(within(detail).getByText("New pricing observation")).toBeInTheDocument();
    expect(within(detail).getByText("Primary Subject fact")).toBeInTheDocument();
    expect(within(detail).getByText("Company Context fact")).toBeInTheDocument();
    if (decision === "thesis") {
      expect(within(detail).getByText("Human invalidated assumption")).toBeInTheDocument();
      expect(within(detail).getByText("Human logic failure")).toBeInTheDocument();
      expect(within(detail).getByText("Human conclusion change")).toBeInTheDocument();
    }
    for (const name of [/accept/i, /approve/i, /activate/i, /reject/i, /modify/i, /save/i, /submit/i, /rebase/i, /generate/i]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    fireEvent.click(within(detail).getByRole("button", { name: "Open Source" }));
    expect(openSource).toHaveBeenCalledWith("SRC_1", "NODE_1");
  });

  it.each(["STALE_TARGET_VIEW", "CANDIDATE_EVIDENCE_CHANGED", "EVIDENCE_INELIGIBLE"])("shows %s as computed alignment without changing pending", async (alignment) => {
    const row = { ...proposal(), canonical_alignment: alignment };
    vi.mocked(getViewProposals).mockResolvedValue([row]);
    vi.mocked(getViewProposal).mockResolvedValue(row);
    render(<ViewProposalReview onOpenSource={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /MLCC · MINOR/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(alignment);
    expect(screen.getByText("PENDING — NOT OFFICIAL CURRENT VIEW")).toBeInTheDocument();
  });

  it("handles missing base and failed detail requests", async () => {
    const row = { ...proposal(), target_official_view: null, diff: null };
    vi.mocked(getViewProposals).mockResolvedValue([row, proposal("material", "PROP_2")]);
    vi.mocked(getViewProposal).mockResolvedValueOnce(row).mockRejectedValueOnce(new Error("missing"));
    render(<ViewProposalReview onOpenSource={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /MLCC · MINOR/ }));
    expect(await screen.findByText(/Target official View unavailable/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /MLCC · MATERIAL/ }));
    expect(await screen.findByText("Unable to load this Human View Proposal.")).toBeInTheDocument();
    expect(screen.queryByText("PENDING — NOT OFFICIAL CURRENT VIEW")).not.toBeInTheDocument();
  });

  it("aborts old detail requests and ignores late results", async () => {
    let resolveOld!: (value: ViewProposalDetail) => void;
    const old = new Promise<ViewProposalDetail>((resolve) => { resolveOld = resolve; });
    vi.mocked(getViewProposals).mockResolvedValue([proposal(), proposal("thesis", "PROP_2")]);
    vi.mocked(getViewProposal).mockReturnValueOnce(old).mockResolvedValueOnce(proposal("thesis", "PROP_2"));
    render(<ViewProposalReview onOpenSource={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /MLCC · MINOR/ }));
    const signal = vi.mocked(getViewProposal).mock.calls[0][1];
    fireEvent.click(screen.getByRole("button", { name: /MLCC · THESIS/ }));
    expect(await screen.findByText("Human invalidated assumption")).toBeInTheDocument();
    expect(signal?.aborted).toBe(true);
    await act(async () => resolveOld(proposal()));
    expect(screen.getByText("Human invalidated assumption")).toBeInTheDocument();
  });
});
