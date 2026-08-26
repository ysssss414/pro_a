import { describe, expect, it } from "vitest";

import type { NeighborGraph } from "../api/types";
import { toCytoscapeElements } from "./GraphPanel";

describe("GraphPanel data mapping", () => {
  it("keeps relation direction and marks the selected center", () => {
    const graph: NeighborGraph = {
      center: { node_id: "NODE_CHILD", canonical_name: "AI Server PCB", primary_type: "Product" },
      nodes: [{ node_id: "NODE_PARENT", canonical_name: "AI Server", primary_type: "Equipment" }],
      edges: [{
        relation_id: "REL_PART",
        from_node_id: "NODE_CHILD",
        relation_type: "part_of",
        to_node_id: "NODE_PARENT",
        scope: "",
        status: "current",
        confidence: 1,
        from_canonical_name: "AI Server PCB",
        to_canonical_name: "AI Server",
      }],
    };

    const elements = toCytoscapeElements(graph);
    expect(elements[0].classes).toBe("center-node");
    expect(elements[2].data).toMatchObject({
      source: "NODE_CHILD",
      target: "NODE_PARENT",
      label: "part_of",
    });
  });
});
