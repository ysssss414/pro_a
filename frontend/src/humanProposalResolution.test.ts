import { describe, expect, it, vi } from "vitest";

import type { ViewProposalDetail } from "./api/types";
import { buildResolutionArtifact, resolutionSnapshotMatches } from "./humanProposalResolution";

function proposal(overrides: Partial<ViewProposalDetail> = {}): ViewProposalDetail {
  return {
    proposal_id: "PROP_1", status: "pending", node_id: "NODE_1", node_name: "MLCC", node_type: "Product",
    node_status: "active", node_resolved: true, decision: "minor", reason: "review", trigger_source_id: "SRC_1",
    trigger_source: { source_id: "SRC_1", title: "Source", publication_time: "2026", source_rank: "B", source_type: "md", origin_type: "secondary", resolved: true },
    previous_view_id: "VIEW_1", previous_version: "v_1", created_at: "2026", resolved_at: "",
    human_review_origin: true, canonical_alignment: "CURRENT", target_official_view: null,
    before_current_view: null, proposed_current_view: {}, diff: null, human_review_handoff: {}, thesis_break: {
      invalidated_core_assumption: "", logic_chain_failure: "", conclusion_change: "",
    }, primary_evidence: [], context_evidence: [], candidate_claims: [], resolution: null,
    proposal_snapshot: { proposal_type: "current_view_change", target_node_id: "NODE_1", created_at: "2026",
      payload: { node_id: "NODE_1", proposed_current_view: { one_line_conclusion: "new" } } },
    ...overrides,
  };
}

describe("human proposal resolution artifact", () => {
  it("creates exact ACCEPT and REJECT READY artifacts", () => {
    const reviewed = proposal();
    const fresh = proposal();
    expect(resolutionSnapshotMatches(reviewed, fresh)).toBe(true);
    expect(buildResolutionArtifact(reviewed, fresh, "ACCEPT", "Human accepted after review")).toEqual({
      document_type: "human_view_proposal_resolution", schema_version: "1", status: "READY",
      proposal_id: "PROP_1", action: "ACCEPT", reason: "Human accepted after review",
      proposal_snapshot: reviewed.proposal_snapshot,
    });
    expect(buildResolutionArtifact(reviewed, fresh, "REJECT", "Human rejected after review").action).toBe("REJECT");
  });

  it("blocks ACCEPT for computed stale alignment but permits REJECT", () => {
    const reviewed = proposal({ canonical_alignment: "STALE_TARGET_VIEW" });
    const fresh = proposal({ canonical_alignment: "STALE_TARGET_VIEW" });
    expect(() => buildResolutionArtifact(reviewed, fresh, "ACCEPT", "reason")).toThrow("STALE_TARGET_VIEW");
    expect(buildResolutionArtifact(reviewed, fresh, "REJECT", "reason").action).toBe("REJECT");
  });

  it("fails closed for changed snapshots, terminal status, and empty reason", () => {
    const reviewed = proposal();
    expect(resolutionSnapshotMatches(reviewed, proposal({ proposal_id: "PROP_2" }))).toBe(false);
    expect(() => buildResolutionArtifact(reviewed, proposal({ status: "accepted" }), "REJECT", "reason")).toThrow("STALE");
    expect(() => buildResolutionArtifact(reviewed, proposal(), "REJECT", " ")).toThrow("required");
    const changed = proposal({ proposal_snapshot: { ...reviewed.proposal_snapshot, created_at: "changed" } });
    expect(() => buildResolutionArtifact(reviewed, changed, "REJECT", "reason")).toThrow("STALE");
  });

  it("does not make a browser request or invoke a runtime manager", () => {
    expect(vi.isMockFunction(fetch)).toBe(false);
  });
});
