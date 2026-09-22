import { describe, expect, it } from "vitest";

import {
  currentViewSummary, relationSummary, selectInspectorClaims, selectLatestEvidence,
  selectOpenGaps, selectRelatedSources, type InspectorClaim, type InspectorData,
} from "./inspectorSelection";

const claim = (id: string, date: string, role: string): InspectorClaim => ({
  claim_id: id, statement: id, business_date: date, status: "current", source_id: "S", source_title: "Source",
  linked_nodes: [{ node_id: "N", role }],
});

function fixture(): InspectorData {
  return { node: { node_id: "N", canonical_name: "Node", primary_type: "Product", status: "active", aliases: [] },
    current_view: { version: "v1", trigger_claim_ids: ["T2", "MISSING", "T1"],
      content_json: { one_line_conclusion: "Recorded conclusion", core_logic: ["one", "two"],
        key_facts: ["three", "four"], recent_change: "Recorded change" } },
    claims: { total: 7, limit: 20, items: [claim("C2", "2026-05-01", "context"),
      claim("S2", "2026-05-02", "subject"), claim("T1", "2020-01-01", "subject"),
      claim("S1", "2026-05-02", "subject"), claim("T2", "2021-01-01", "related"),
      claim("R", "2026-09-01", "related"), claim("C1", "2026-05-01", "context")] },
    sources: [{ source_id: "S", title: "Source", source_type: "filing", source_rank: "A" }],
    relations: [{ relation_id: "R1", from_name: "A", to_name: "B", relation_type: "part_of", status: "current", evidence_count: 0 },
      { relation_id: "R2", from_name: "A", to_name: "C", relation_type: "depends_on", status: "categorical", evidence_count: 0 },
      { relation_id: "R3", from_name: "A", to_name: "D", relation_type: "part_of", status: "historical", evidence_count: 0 }],
    research_question: null, knowledge_gaps: [
      { gap_id: "1", title: "Open", status: "open" }, { gap_id: "2", title: "Done", status: "resolved" },
      { gap_id: "3", title: "Refresh", status: "needs_refresh" }, { gap_id: "4", title: "Again", status: "reopened" }],
    impact: { items: [] }, notes: [], coverage: { sources: 1 } };
}

describe("Unified Inspector exact selection", () => {
  it("preserves available official trigger order, then subject, context and related with date/ID ties", () => {
    const selected = selectInspectorClaims(fixture());
    expect(selected.map(({ claim }) => claim.claim_id)).toEqual(["T2", "T1", "S1", "S2", "C1", "C2", "R"]);
    expect(selected.map(({ label }) => label)).toEqual(["Official View evidence", "Official View evidence",
      "Subject Claim", "Subject Claim", "Context Claim", "Context Claim", "Related Claim"]);
  });

  it("uses backend business_date for latest evidence with stable ID ties", () => {
    expect(selectLatestEvidence(fixture()).map((item) => item.claim_id))
      .toEqual(["R", "S1", "S2", "C1", "C2", "T2", "T1"]);
  });

  it("keeps backend gap/source order and counts exact relation statuses and types", () => {
    const data = fixture();
    expect(selectOpenGaps(data).map((gap) => gap.gap_id)).toEqual(["1", "3", "4"]);
    expect(selectRelatedSources(data)).toEqual(data.sources);
    data.sources = Array.from({ length: 6 }, (_, index) => ({ ...data.sources[0], source_id: `S${index}` }));
    expect(selectRelatedSources(data, 5).map((source) => source.source_id)).toEqual(["S0", "S1", "S2", "S3", "S4"]);
    expect(relationSummary(data)).toEqual({ count: 3,
      statuses: { current: 1, categorical: 1, historical: 1 }, types: { part_of: 2, depends_on: 1 } });
  });

  it("extracts only recorded compact View fields and handles empty research", () => {
    const data = fixture();
    expect(currentViewSummary(data.current_view)).toEqual({ conclusion: "Recorded conclusion",
      support: ["one", "two", "three"], recentChange: "Recorded change" });
    data.current_view = null; data.claims.items = []; data.knowledge_gaps = []; data.sources = []; data.relations = [];
    expect(currentViewSummary(data.current_view)).toEqual({ conclusion: "", support: [], recentChange: "" });
    expect(selectInspectorClaims(data)).toEqual([]);
    expect(selectLatestEvidence(data)).toEqual([]);
    expect(selectOpenGaps(data)).toEqual([]);
    expect(selectRelatedSources(data)).toEqual([]);
    expect(relationSummary(data).count).toBe(0);
  });
});
