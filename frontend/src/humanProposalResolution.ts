import type { ProposalResolutionArtifact, ViewProposalDetail } from "./api/types";

function ordered(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(ordered);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
      .map(([key, item]) => [key, ordered(item)]));
  }
  return value;
}

export function resolutionSnapshotMatches(reviewed: ViewProposalDetail, fresh: ViewProposalDetail): boolean {
  return reviewed.proposal_id === fresh.proposal_id && fresh.status === "pending"
    && JSON.stringify(ordered(reviewed.proposal_snapshot)) === JSON.stringify(ordered(fresh.proposal_snapshot));
}

export function buildResolutionArtifact(reviewed: ViewProposalDetail, fresh: ViewProposalDetail,
  action: "ACCEPT" | "REJECT", reason: string): ProposalResolutionArtifact {
  if (reviewed.status !== "pending" || !resolutionSnapshotMatches(reviewed, fresh)) {
    throw new Error("RESOLUTION_ARTIFACT_STALE — Proposal changed. Reopen it to review; no snapshot was updated.");
  }
  if (!reason.trim() || !["ACCEPT", "REJECT"].includes(action)) throw new Error("Resolution action and reason are required.");
  if (action === "ACCEPT" && (reviewed.canonical_alignment !== "CURRENT" || fresh.canonical_alignment !== "CURRENT")) {
    throw new Error(`ACCEPT blocked: ${fresh.canonical_alignment !== "CURRENT" ? fresh.canonical_alignment : reviewed.canonical_alignment}`);
  }
  return { document_type: "human_view_proposal_resolution", schema_version: "1", status: "READY",
    proposal_id: reviewed.proposal_id, action, reason, proposal_snapshot: structuredClone(reviewed.proposal_snapshot) };
}

export function downloadResolutionArtifact(artifact: ProposalResolutionArtifact): void {
  const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `human-view-proposal-resolution-${artifact.proposal_id}-${artifact.action}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
