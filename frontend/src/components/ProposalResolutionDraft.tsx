import { useEffect, useRef, useState } from "react";

import { getViewProposal } from "../api/client";
import type { ViewProposalDetail } from "../api/types";
import { buildResolutionArtifact, downloadResolutionArtifact, resolutionSnapshotMatches } from "../humanProposalResolution";

export function ProposalResolutionDraft({ proposal }: { proposal: ViewProposalDetail }) {
  const [action, setAction] = useState<"" | "ACCEPT" | "REJECT">("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const [alignment, setAlignment] = useState(proposal.canonical_alignment);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  const exportResolution = async () => {
    if (!action || !reason.trim() || stale || busy) return;
    const controller = new AbortController();
    request.current?.abort();
    request.current = controller;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const fresh = await getViewProposal(proposal.proposal_id, controller.signal);
      if (controller.signal.aborted) return;
      setStale(!resolutionSnapshotMatches(proposal, fresh));
      setAlignment(fresh.canonical_alignment);
      downloadResolutionArtifact(buildResolutionArtifact(proposal, fresh, action, reason));
      setMessage("READY resolution exported locally. No Production write occurred.");
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Unable to revalidate Proposal.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  if (proposal.status !== "pending") return null;
  return <section className="current-view-section resolution-draft" aria-label="Local proposal resolution">
    <h3>Local resolution draft — not canonical</h3>
    <p>NON-CANONICAL PROPOSAL RESOLUTION ARTIFACT</p>
    <p>Export only. Canonical mutation requires the explicit CLI gateway and separate authorization.</p>
    {stale ? <p role="alert">RESOLUTION_ARTIFACT_STALE — Reopen the Proposal to review it again.</p> : <fieldset disabled={busy}>
      <label htmlFor="resolution-action">Resolution action</label>
      <select id="resolution-action" value={action} onChange={(event) => setAction(event.target.value as typeof action)}>
        <option value="">Choose an action</option>
        <option value="ACCEPT" disabled={proposal.canonical_alignment !== "CURRENT" || alignment !== "CURRENT"}>ACCEPT</option>
        <option value="REJECT">REJECT</option>
      </select>
      {alignment !== "CURRENT" && <p>ACCEPT READY export blocked: {alignment}. REJECT is still available.</p>}
      <label htmlFor="resolution-reason">Resolution Reason</label>
      <textarea id="resolution-reason" value={reason} onChange={(event) => setReason(event.target.value)} rows={3} />
      <button type="button" disabled={!action || !reason.trim() || (action === "ACCEPT" && alignment !== "CURRENT")}
        onClick={() => void exportResolution()}>Export Resolution JSON</button>
    </fieldset>}
    {busy && <p role="status">Revalidating Proposal before export…</p>}
    {error && !stale && <p role="alert">{error}</p>}
    {message && <p role="status">{message}</p>}
  </section>;
}
