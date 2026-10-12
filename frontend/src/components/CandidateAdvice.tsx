import { useState } from "react";
import { request } from "../api/workbench";

export function CandidateAdvice({ handle, csrf }: { handle: string; csrf: string }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function exportContext() {
    setBusy(true); setMessage("");
    try {
      const value = await request<object>(`/reviews/${handle}/advice-context`, new AbortController().signal);
      const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "frozen-review-context.json"; link.click();
      URL.revokeObjectURL(url);
      setMessage("Use this same frozen context for independent A and B reviews.");
    } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
  }
  async function submit(file: File) {
    if (file.size > 2_000_000) { setMessage("Advice file exceeds 2 MB."); return; }
    setBusy(true); setMessage("");
    try {
      const value = await request<{ slot: string; reviewer_id: string }>(`/reviews/${handle}/advice`, new AbortController().signal,
        { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(JSON.parse(await file.text())) });
      setMessage(`${value.slot} opinion registered for ${value.reviewer_id}. Human decisions and Seal are still required.`);
    } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
  }
  return <section aria-label="Independent candidate advice"><h3>Independent A/B review</h3>
    <p>Source assertions remain unverified and clue only. Each reviewer submits their identity, context SHA, and an explicit judgment and reason for every candidate. Model advice cannot act as Human authorization.</p>
    <button type="button" disabled={busy} onClick={() => void exportContext()}>Export frozen review context</button>
    <label>Import one actual reviewer opinion (JSON)<input type="file" accept="application/json,.json" disabled={busy}
      onChange={event => { const file = event.target.files?.[0]; if (file) void submit(file); event.target.value = ""; }} /></label>
    {message && <p role="status">{message}</p>}
  </section>;
}
