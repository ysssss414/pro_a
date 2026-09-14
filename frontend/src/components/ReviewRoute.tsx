import { useCallback, useEffect, useRef, useState } from "react";
import { getPacket, getSession, listPackets, loginWorkbench, WorkbenchError } from "../api/workbench";
import type { PacketSummary, ReviewPacket } from "../api/workbench";
import { ReviewItemDetail } from "./ReviewItemDetail";
import { PersistentReview } from "./PersistentReview";
import "./ReviewRoute.css";

const show = (value: unknown) => value === undefined || value === null || value === "" ? "Not provided in native packet" : typeof value === "string" ? value : JSON.stringify(value, null, 2);

export function ReviewRoute({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [needsLogin, setNeedsLogin] = useState(false);
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("");
  const [csrf, setCsrf] = useState("");
  const [packets, setPackets] = useState<PacketSummary[]>([]);
  const [packet, setPacket] = useState<ReviewPacket | null>(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(async (credential?: string, handle?: string) => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setLoading(true);
    setError("");
    setPacket(null);
    try {
      if (credential !== undefined) await loginWorkbench(credential, current.signal);
      const session = await getSession(current.signal);
      const result = await listPackets(current.signal);
      const id = handle ?? result.packets[0]?.artifact_id;
      const detail = id ? await getPacket(id, current.signal) : null;
      if (current.signal.aborted) return;
      setNeedsLogin(false);
      setMode(session.mode);
      setCsrf(session.csrf_token ?? "");
      setPackets(result.packets);
      setPacket(detail);
      setSelected(detail?.items[0]?.candidate_id ?? "");
      onAuthenticated();
    } catch (caught) {
      if (current.signal.aborted) return;
      setPackets([]);
      setMode("");
      setNeedsLogin(caught instanceof WorkbenchError && caught.status === 401);
      setError(caught instanceof WorkbenchError ? caught.message : "Workbench unavailable. Retry after checking the application.");
    } finally {
      if (!current.signal.aborted) setLoading(false);
    }
  }, [onAuthenticated]);

  useEffect(() => {
    void load();
    return () => controller.current?.abort();
  }, [load]);

  const refresh = async () => {
    if (!packet) throw new Error("No registered review selected");
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    try {
      const detail = await getPacket(packet.artifact_id, current.signal);
      if (!current.signal.aborted) setPacket(detail);
      return detail;
    } catch (error) {
      if (error instanceof WorkbenchError && error.status === 401) { setNeedsLogin(true); setPacket(null); }
      throw error;
    }
  };

  const item = packet?.items.find((row) => row.candidate_id === selected);

  return <main className="review-route">
    <header>
      <h1>Native Review</h1>
      <p>{packet?.review?.enabled ? "Human review only. Saving or sealing does not modify Production or authorize promotion." : "Stage 0 · Read-only. Native decision capabilities are metadata; decision saving is unavailable."}</p>
      {mode && <strong className="review-mode">{mode} · operator session</strong>}
    </header>
    {error && <p role="alert">{error}</p>}
    {needsLogin && <form onSubmit={(event) => { event.preventDefault(); const credential = token; setToken(""); void load(credential); }}>
      <label>Workbench session token <input type="password" autoComplete="off" required minLength={32} value={token} onChange={(event) => setToken(event.target.value)} /></label>
      <button type="submit" disabled={loading}>Sign in</button>
    </form>}
    {loading && <p role="status">Validating registered packet…</p>}
    {!loading && !needsLogin && <button type="button" onClick={() => void load(undefined, packet?.artifact_id)}>Refresh validated packet</button>}
    {!loading && !needsLogin && !error && packets.length === 0 && <p>No registered packets. An operator must register a native blank packet.</p>}
    {packet && <>
      <label>Registered packet <select value={packet.artifact_id} onChange={(event) => void load(undefined, event.target.value)}>
        {packets.map((entry) => <option key={entry.artifact_id} value={entry.artifact_id}>{entry.packet_id}</option>)}
      </select></label>
      <section aria-label="Packet identity">
        <h2>Packet and Source</h2>
        <dl><dt>Packet</dt><dd>{packet.packet_id}</dd><dt>Run</dt><dd>{packet.run_id}</dd>
          <dt>Validation</dt><dd>{packet.validation_state}</dd><dt>Packet status</dt><dd>{packet.packet_status}</dd>
          <dt>Packet file SHA-256</dt><dd>{packet.packet_file_sha256}</dd><dt>Immutable packet SHA-256</dt><dd>{packet.immutable_packet_sha256}</dd>
          <dt>Source</dt><dd>{packet.source.source_id}</dd><dt>Source SHA-256</dt><dd>{packet.source.source_sha256}</dd>
          <dt>Source type / bytes</dt><dd>{packet.source.source_type} / {packet.source.size_bytes}</dd>
        </dl>
      </section>
      <section aria-label="Native counts"><h2>Native item counts</h2><dl>
        {Object.entries(packet.summary).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}
      </dl></section>
      <section aria-label="Exclusions"><h2>Excluded / non-reviewable</h2>
        <p>{packet.excluded_relation_inventory.count} excluded functional relations · review reopened: {String(packet.excluded_relation_inventory.relation_review_reopened)}</p>
        <p>{packet.excluded_relation_inventory.policy}</p>
        <pre>{show(packet.excluded_relation_inventory.candidate_ids)}</pre>
        <p>Aliases remain part of native Node identity; they have no separate decision controls.</p>
      </section>
      {packet.review?.enabled ? <PersistentReview key={packet.artifact_id} packet={packet} review={packet.review} csrf={csrf} refresh={refresh} /> : <div className="review-items">
        <section aria-label="Review items"><h2>Native items ({packet.items.length})</h2>
          {packet.items.map((row) => <button type="button" key={row.candidate_id} aria-pressed={selected === row.candidate_id} onClick={() => setSelected(row.candidate_id)}>
            {row.candidate_type} · {row.candidate_id}
          </button>)}
        </section>
        {item && <ReviewItemDetail item={item} />}
      </div>}
    </>}
  </main>;
}
