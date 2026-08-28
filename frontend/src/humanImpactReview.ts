import type {
  ClaimNodeRole,
  CurrentViewResult,
  ImpactCandidate,
  ImpactClaimSummary,
  SourceClaim,
  SourceDetail,
} from "./api/types";

export type HumanImpactDecision = "NO_CHANGE" | "MINOR" | "MATERIAL" | "THESIS";
export type HumanImpactReviewStatus = "DRAFT" | "READY" | "STALE";

export interface CandidateClaimSnapshot {
  claim_id: string;
  role: ClaimNodeRole;
}

export interface ThesisBreak {
  invalidated_core_assumption: string;
  logic_chain_failure: string;
  conclusion_change: string;
}

export interface HumanImpactReviewDraft {
  document_type: "human_impact_review";
  schema_version: "1";
  status: HumanImpactReviewStatus;
  source_id: string;
  node_id: string;
  node_name: string;
  node_type: string;
  target_view_id: string;
  target_view_version: string;
  decision: HumanImpactDecision | "";
  reason: string;
  selected_primary_claim_ids: string[];
  selected_context_claim_ids: string[];
  candidate_claims: CandidateClaimSnapshot[];
  thesis_break: ThesisBreak;
  evidence_sufficiency: "NOT_EVALUATED";
  updated_at: string;
}

export interface ReviewValidation {
  status: HumanImpactReviewStatus;
  ready: boolean;
  issues: string[];
}

export interface ReviewClaim extends ImpactClaimSummary {
  nature: string;
  evidence_excerpt: string;
  evidence_pointer: string;
  attributed_to: string;
}

export const DECISION_LABELS: Record<HumanImpactDecision, string> = {
  NO_CHANGE: "No Change",
  MINOR: "Minor",
  MATERIAL: "Material",
  THESIS: "Thesis Change",
};

export const DECISIONS: HumanImpactDecision[] = ["NO_CHANGE", "MINOR", "MATERIAL", "THESIS"];

const LOCAL_STORAGE_PREFIX = "human-impact-review:";
const NON_PRIMARY_STATUSES = new Set(["needs_review", "invalidated", "superseded"]);

function storagePrefix(sourceId: string, nodeId: string): string {
  return `${LOCAL_STORAGE_PREFIX}${encodeURIComponent(sourceId)}:${encodeURIComponent(nodeId)}:`;
}

export function reviewStorageKey(sourceId: string, nodeId: string, targetViewId: string): string {
  return `${storagePrefix(sourceId, nodeId)}${encodeURIComponent(targetViewId)}`;
}

export function createReviewDraft(
  source: SourceDetail,
  candidate: ImpactCandidate,
  targetView: CurrentViewResult,
): HumanImpactReviewDraft {
  return {
    document_type: "human_impact_review",
    schema_version: "1",
    status: "DRAFT",
    source_id: source.source_id,
    node_id: candidate.node.node_id,
    node_name: candidate.node.canonical_name,
    node_type: candidate.node.primary_type,
    target_view_id: targetView.view_id,
    target_view_version: targetView.version,
    decision: "",
    reason: "",
    selected_primary_claim_ids: [],
    selected_context_claim_ids: [],
    candidate_claims: candidateClaimSnapshot(candidate),
    thesis_break: {
      invalidated_core_assumption: "",
      logic_chain_failure: "",
      conclusion_change: "",
    },
    evidence_sufficiency: "NOT_EVALUATED",
    updated_at: new Date().toISOString(),
  };
}

export function candidateClaimSnapshot(candidate: ImpactCandidate): CandidateClaimSnapshot[] {
  return candidate.claims.map((claim) => ({ claim_id: claim.claim_id, role: claim.role }));
}

function sortedSnapshot(snapshot: CandidateClaimSnapshot[]): string[] {
  return snapshot
    .map((claim) => `${claim.claim_id}\u0000${claim.role}`)
    .sort();
}

export function candidateEvidenceChanged(
  draft: HumanImpactReviewDraft,
  candidate: ImpactCandidate,
): boolean {
  return JSON.stringify(sortedSnapshot(draft.candidate_claims))
    !== JSON.stringify(sortedSnapshot(candidateClaimSnapshot(candidate)));
}

function readStoredDraft(key: string): HumanImpactReviewDraft | null {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as HumanImpactReviewDraft;
    if (parsed.document_type !== "human_impact_review" || parsed.schema_version !== "1") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function loadReviewDraft(
  sourceId: string,
  nodeId: string,
  targetViewId: string,
): HumanImpactReviewDraft | null {
  const exact = readStoredDraft(reviewStorageKey(sourceId, nodeId, targetViewId));
  if (exact) return exact;
  try {
    const prefix = storagePrefix(sourceId, nodeId);
    const drafts: HumanImpactReviewDraft[] = [];
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (!key?.startsWith(prefix)) continue;
      const draft = readStoredDraft(key);
      if (draft) drafts.push(draft);
    }
    return drafts.sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0] ?? null;
  } catch {
    return null;
  }
}

export function saveReviewDraft(draft: HumanImpactReviewDraft): boolean {
  try {
    window.localStorage.setItem(
      reviewStorageKey(draft.source_id, draft.node_id, draft.target_view_id),
      JSON.stringify({ ...draft, updated_at: new Date().toISOString() }),
    );
    return true;
  } catch {
    return false;
  }
}

export function isPrimaryEligible(claim: ImpactClaimSummary): boolean {
  return claim.role === "subject" && !NON_PRIMARY_STATUSES.has(claim.status.trim().toLowerCase());
}

export function validateReviewDraft(
  draft: HumanImpactReviewDraft,
  candidate: ImpactCandidate,
  currentView: CurrentViewResult | null,
): ReviewValidation {
  if (!currentView) {
    return { status: "DRAFT", ready: false, issues: ["Latest official Current View is still loading."] };
  }

  const issues: string[] = [];
  const targetStale = draft.target_view_id !== currentView.view_id
    || draft.target_view_version !== currentView.version;
  const candidateChanged = candidateEvidenceChanged(draft, candidate);
  if (targetStale) issues.push("STALE TARGET VIEW");
  if (candidateChanged) issues.push("CANDIDATE EVIDENCE CHANGED");

  const byId = new Map(candidate.claims.map((claim) => [claim.claim_id, claim]));
  const primaryIds = new Set(draft.selected_primary_claim_ids);
  const contextIds = new Set(draft.selected_context_claim_ids);
  if (primaryIds.size !== draft.selected_primary_claim_ids.length) issues.push("Duplicate Primary Evidence selection.");
  if (contextIds.size !== draft.selected_context_claim_ids.length) issues.push("Duplicate Context Evidence selection.");
  if ([...primaryIds].some((id) => {
    const claim = byId.get(id);
    return !claim || !isPrimaryEligible(claim);
  })) {
    issues.push("Primary Evidence must be eligible Subject Claims.");
  }
  if ([...contextIds].some((id) => byId.get(id)?.role !== "context")) {
    issues.push("Context Evidence must be Context Claims.");
  }
  if (!draft.decision) issues.push("Select a decision.");
  if (!draft.reason.trim()) issues.push("Reason is required.");
  if (draft.decision && draft.decision !== "NO_CHANGE" && primaryIds.size === 0) {
    issues.push("Minor, Material, and Thesis Change require at least one eligible Subject Claim.");
  }
  if (draft.decision === "THESIS") {
    if (!draft.thesis_break.invalidated_core_assumption.trim()) issues.push("Thesis Change requires the invalidated core assumption.");
    if (!draft.thesis_break.logic_chain_failure.trim()) issues.push("Thesis Change requires the logic-chain failure.");
    if (!draft.thesis_break.conclusion_change.trim()) issues.push("Thesis Change requires the conclusion change.");
  }

  return {
    status: targetStale || candidateChanged ? "STALE" : issues.length === 0 ? "READY" : "DRAFT",
    ready: issues.length === 0,
    issues,
  };
}

export function reviewClaims(source: SourceDetail, candidate: ImpactCandidate): ReviewClaim[] {
  const sourceClaims = new Map(source.claims.map((claim) => [claim.claim_id, claim]));
  return candidate.claims.map((summary) => {
    const sourceClaim: SourceClaim | undefined = sourceClaims.get(summary.claim_id);
    return {
      ...summary,
      nature: sourceClaim?.nature ?? "—",
      evidence_excerpt: sourceClaim?.evidence_excerpt ?? "",
      evidence_pointer: sourceClaim?.evidence_pointer ?? "",
      attributed_to: sourceClaim?.attributed_to ?? "",
    };
  });
}

export function buildReviewArtifact(
  draft: HumanImpactReviewDraft,
  source: SourceDetail,
): Record<string, unknown> {
  return {
    document_type: draft.document_type,
    schema_version: draft.schema_version,
    status: "READY",
    source: {
      source_id: source.source_id,
      title: source.title,
      publication_time: source.publication_time,
      source_rank: source.source_rank,
      source_type: source.source_type,
      origin_type: source.origin_type,
    },
    source_id: draft.source_id,
    node_id: draft.node_id,
    node_name: draft.node_name,
    node_type: draft.node_type,
    target_view_id: draft.target_view_id,
    target_view_version: draft.target_view_version,
    decision: draft.decision.toLowerCase(),
    reason: draft.reason.trim(),
    selected_primary_claim_ids: [...draft.selected_primary_claim_ids],
    selected_context_claim_ids: [...draft.selected_context_claim_ids],
    candidate_claims: draft.candidate_claims.map((claim) => ({ ...claim })),
    thesis_break: { ...draft.thesis_break },
    evidence_sufficiency: "NOT_EVALUATED",
  };
}

export function downloadReviewArtifact(artifact: Record<string, unknown>): void {
  const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `human-impact-review-${String(artifact.source_id)}-${String(artifact.node_id)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
