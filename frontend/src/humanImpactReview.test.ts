import { beforeEach, describe, expect, it } from "vitest";

import type { CurrentViewResult, ImpactCandidate, SourceDetail } from "./api/types";
import {
  buildReviewArtifact,
  candidateEvidenceChanged,
  createReviewDraft,
  loadReviewDraft,
  reviewStorageKey,
  saveReviewDraft,
  validateReviewDraft,
} from "./humanImpactReview";

const source: SourceDetail = {
  source_id: "SRC_FIXTURE",
  title: "Fixture Source",
  original_name: "fixture.md",
  source_type: "research_report",
  source_rank: "A",
  origin_type: "local_file",
  author: "Analyst",
  organization: "Research Org",
  publication_time: "2026-08-27",
  ingested_at: "2026-08-27",
  ingestion_mode: "standard",
  analysis_mode: "standard",
  status: "analyzed",
  underlying_source_id: "",
  linked_nodes: [],
  claims: [],
};

const view: CurrentViewResult = {
  view_id: "VIEW_FIXTURE_1",
  node_id: "NODE_FIXTURE",
  version: "v_20260827",
  status: "official",
  change_level: "initial",
  previous_view_id: null,
  content_md: "Fixture View",
  content_json: { one_line_conclusion: "Fixture judgment." },
  trigger_source_id: null,
  trigger_claim_ids: [],
  revision_date: "20260827",
  revision_seq: 0,
  accepted_proposal_id: "PROP_FIXTURE",
  created_at: "2026-08-27",
  confirmed_at: "2026-08-27",
};

const candidate: ImpactCandidate = {
  node: { node_id: "NODE_FIXTURE", canonical_name: "Fixture Node", primary_type: "Product" },
  current_view: { view_id: view.view_id, version: view.version, change_level: "initial", revision_date: view.revision_date },
  roles: ["subject", "context", "related"],
  claims: [
    { claim_id: "CLAIM_SUBJECT", statement: "Direct fact", status: "current", confidence: 0.95, role: "subject", fact_time: "2026-08-26", publication_time: "2026-08-27" },
    { claim_id: "CLAIM_CONTEXT", statement: "Context fact", status: "current", confidence: 0.8, role: "context", fact_time: "2026-08-25", publication_time: "2026-08-27" },
    { claim_id: "CLAIM_REVIEW", statement: "Unresolved fact", status: "needs_review", confidence: 0, role: "subject", fact_time: "2026-08-24", publication_time: "2026-08-27" },
    { claim_id: "CLAIM_RELATED", statement: "Association", status: "current", confidence: 0.7, role: "related", fact_time: "2026-08-23", publication_time: "2026-08-27" },
  ],
};

function draftFor(currentCandidate = candidate, currentView = view) {
  return createReviewDraft(source, currentCandidate, currentView);
}

function withDecision(
  decision: "NO_CHANGE" | "MINOR" | "MATERIAL" | "THESIS",
  changes: Partial<ReturnType<typeof draftFor>> = {},
) {
  return {
    ...draftFor(),
    decision,
    reason: "A human reviewer recorded this decision.",
    ...changes,
  };
}

describe("human impact review contract", () => {
  beforeEach(() => window.localStorage.clear());

  it("allows a reasoned NO_CHANGE without Primary Evidence", () => {
    const result = validateReviewDraft(withDecision("NO_CHANGE"), candidate, view);
    expect(result).toEqual({ status: "READY", ready: true, issues: [] });
    const artifact = buildReviewArtifact(withDecision("NO_CHANGE"), source);
    expect(artifact).toMatchObject({
      status: "READY",
      decision: "no_change",
      selected_primary_claim_ids: [],
      evidence_sufficiency: "NOT_EVALUATED",
    });
    expect(artifact).toHaveProperty("source.source_id", "SRC_FIXTURE");
    expect(artifact).toHaveProperty("target_view_id", "VIEW_FIXTURE_1");
    expect(artifact).toHaveProperty("candidate_claims", [
      { claim_id: "CLAIM_SUBJECT", role: "subject" },
      { claim_id: "CLAIM_CONTEXT", role: "context" },
      { claim_id: "CLAIM_REVIEW", role: "subject" },
      { claim_id: "CLAIM_RELATED", role: "related" },
    ]);
  });

  it("requires eligible Subject Evidence for MINOR", () => {
    expect(validateReviewDraft(withDecision("MINOR"), candidate, view).ready).toBe(false);
    const result = validateReviewDraft(withDecision("MINOR", {
      selected_primary_claim_ids: ["CLAIM_SUBJECT"],
    }), candidate, view);
    expect(result).toEqual({ status: "READY", ready: true, issues: [] });
  });

  it("keeps MATERIAL governance as a reminder and never evaluates sufficiency", () => {
    const draft = withDecision("MATERIAL", { selected_primary_claim_ids: ["CLAIM_SUBJECT"] });
    expect(validateReviewDraft(draft, candidate, view).ready).toBe(true);
    expect(buildReviewArtifact(draft, source).evidence_sufficiency).toBe("NOT_EVALUATED");
  });

  it("requires all structured Thesis Change reason fields", () => {
    const draft = withDecision("THESIS", { selected_primary_claim_ids: ["CLAIM_SUBJECT"] });
    expect(validateReviewDraft(draft, candidate, view).ready).toBe(false);
    const complete = {
      ...draft,
      thesis_break: {
        invalidated_core_assumption: "Demand assumption failed.",
        logic_chain_failure: "The operating logic no longer holds.",
        conclusion_change: "The official conclusion must be reconsidered.",
      },
    };
    expect(validateReviewDraft(complete, candidate, view)).toEqual({ status: "READY", ready: true, issues: [] });
  });

  it("allows context-only candidates to close with NO_CHANGE but not a change-level READY artifact", () => {
    const contextOnly: ImpactCandidate = {
      ...candidate,
      roles: ["context", "related"],
      claims: candidate.claims.filter((claim) => claim.role !== "subject"),
    };
    expect(validateReviewDraft(withDecision("NO_CHANGE", { candidate_claims: contextOnly.claims.map((claim) => ({ claim_id: claim.claim_id, role: claim.role })) }), contextOnly, view).ready).toBe(true);
    const material = withDecision("MATERIAL", { selected_primary_claim_ids: [] });
    expect(validateReviewDraft(material, contextOnly, view).ready).toBe(false);
  });

  it("blocks a draft when the target official View changed", () => {
    const latest = { ...view, view_id: "VIEW_FIXTURE_2", version: "v_20260828" };
    const result = validateReviewDraft(withDecision("NO_CHANGE"), candidate, latest);
    expect(result.status).toBe("STALE");
    expect(result.ready).toBe(false);
    expect(result.issues).toContain("STALE TARGET VIEW");
  });

  it("blocks a draft when a candidate Claim role changed", () => {
    const changedCandidate: ImpactCandidate = {
      ...candidate,
      claims: candidate.claims.map((claim) => claim.claim_id === "CLAIM_SUBJECT" ? { ...claim, role: "context" as const } : claim),
    };
    expect(candidateEvidenceChanged(withDecision("NO_CHANGE"), changedCandidate)).toBe(true);
    const result = validateReviewDraft(withDecision("NO_CHANGE"), changedCandidate, view);
    expect(result.status).toBe("STALE");
    expect(result.issues).toContain("CANDIDATE EVIDENCE CHANGED");
  });

  it("isolates local drafts by Source, Node, and target View", () => {
    const first = withDecision("NO_CHANGE");
    const second = withDecision("MINOR", {
      source_id: "SRC_OTHER",
      node_id: "NODE_OTHER",
      target_view_id: "VIEW_FIXTURE_1",
      target_view_version: "v_20260827",
    });
    const third = withDecision("MATERIAL", { target_view_id: "VIEW_FIXTURE_2", target_view_version: "v_20260828" });
    expect(saveReviewDraft(first)).toBe(true);
    expect(saveReviewDraft(second)).toBe(true);
    expect(saveReviewDraft(third)).toBe(true);
    expect(reviewStorageKey(source.source_id, first.node_id, first.target_view_id)).not.toBe(
      reviewStorageKey(source.source_id, second.node_id, second.target_view_id),
    );
    expect(loadReviewDraft(source.source_id, first.node_id, first.target_view_id)?.decision).toBe("NO_CHANGE");
    expect(loadReviewDraft(second.source_id, second.node_id, second.target_view_id)?.decision).toBe("MINOR");
    expect(loadReviewDraft(source.source_id, third.node_id, third.target_view_id)?.decision).toBe("MATERIAL");
  });
});
