import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { KnowledgeGapResult, ResearchQuestionResult } from "../api/types";
import { ResearchTab } from "./ResearchTab";

const researchQuestion: ResearchQuestionResult = {
  rq_id: "RQ_1",
  node_id: "NODE_EML",
  question: "Will optical adoption accelerate?",
  importance: "Material to demand.",
  current_answer: "Adoption is accelerating.",
  confidence: 0.72,
  supporting_claim_ids: ["CLAIM_1"],
  opposing_claim_ids: ["CLAIM_2"],
  key_variables: ["hyperscaler capex", { variable: "pricing", direction: "down" }],
  supporting_claims: [{ claim_id: "CLAIM_1", statement: "Demand is growing.", status: "current", confidence: 0.9 }],
  opposing_claims: [{ claim_id: "CLAIM_2", statement: "Pricing is falling.", status: "current", confidence: 0.6 }],
  what_would_change_my_mind: "A sustained deployment delay.",
  status: "open",
  created_at: "2026-02-01",
  updated_at: "2026-03-01",
};

const gaps: KnowledgeGapResult[] = [{
  gap_id: "GAP_1",
  node_id: "NODE_EML",
  title: "Track adoption",
  description: "Measure deployment timing.",
  status: "open",
  source_claim_ids: ["CLAIM_1"],
  freshness_due: "2026-05-01",
  resolution_claim_id: "",
  superseded_by_gap_id: "",
  created_at: "2026-02-01",
  updated_at: "2026-03-01",
}];

describe("ResearchTab", () => {
  it("renders the question, answer, variables, falsifier, evidence, and gaps", () => {
    render(
      <ResearchTab
        researchQuestion={researchQuestion}
        knowledgeGaps={gaps}
        loading={false}
        researchError={null}
        gapsError={null}
      />,
    );

    expect(screen.getByRole("heading", { name: "Will optical adoption accelerate?" })).toBeInTheDocument();
    expect(screen.getByText("Adoption is accelerating.")).toBeInTheDocument();
    expect(screen.getByText("hyperscaler capex")).toBeInTheDocument();
    expect(screen.getByText("variable: pricing · direction: down")).toBeInTheDocument();
    expect(screen.getByText("A sustained deployment delay.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Supporting Evidence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Opposing Evidence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Track adoption" })).toBeInTheDocument();
  });
});
