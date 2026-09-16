import type { ReactNode } from "react";
import type { NativeItem } from "../api/workbench";

export const showNative = (value: unknown) => value === undefined || value === null || value === "" ? "Not provided in native packet" : typeof value === "string" ? value : JSON.stringify(value, null, 2);

export function ReviewItemDetail({ item, children, persistent = false }: { item: NativeItem; children?: ReactNode; persistent?: boolean }) {
  const evidence = item.content.evidence_validation as { authoritative_locator?: Record<string, unknown> } | undefined;
  const locator = evidence?.authoritative_locator;
  return <section aria-label="Selected item">
    <h2>{item.candidate_type} · {item.candidate_id}</h2>
    <h3>Evidence</h3>
    <dl><dt>Pointer</dt><dd>{showNative(item.content.evidence_pointer)}</dd>
      <dt>Excerpt</dt><dd>{showNative(item.content.evidence_excerpt)}</dd>
      <dt>Page</dt><dd>{showNative(locator?.page ?? locator?.page_number)}</dd>
      <dt>Section</dt><dd>{showNative(locator?.section)}</dd><dt>Paragraph</dt><dd>{showNative(locator?.paragraph)}</dd>
    </dl>
    <h3>Supporting evidence</h3><pre>{showNative(item.content.supporting_evidence)}</pre>
    {children}
    <h3>{persistent ? "Native decision semantics" : "Native capabilities · unavailable in Stage 0"}</h3>
    <p>{item.allowed_decisions.join(" · ")}</p><pre>{showNative(item.decision_effects)}</pre>
    <h3>Native content, validation and warnings</h3><pre>{showNative(item.content)}</pre>
    <p>Content SHA-256: {item.content_sha256}</p>
  </section>;
}
