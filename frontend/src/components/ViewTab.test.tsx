import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CurrentViewResult } from "../api/types";
import { ViewTab } from "./ViewTab";

const currentView: CurrentViewResult = {
  view_id: "VIEW_1",
  node_id: "NODE_EML",
  version: "v_20260301_01",
  status: "official",
  change_level: "material",
  previous_view_id: "VIEW_0",
  content_md: "Optical demand is accelerating.",
  content_json: { thesis: "accelerating" },
  trigger_source_id: "SRC_1",
  trigger_claim_ids: ["CLAIM_1"],
  revision_date: "20260301",
  revision_seq: 1,
  accepted_proposal_id: "PROPOSAL_1",
  created_at: "2026-03-01",
  confirmed_at: "2026-03-02",
};

describe("ViewTab", () => {
  it("renders the Current View content, version, revision, and Source action", () => {
    const onOpenSource = vi.fn();
    render(<ViewTab currentView={currentView} loading={false} error={null} onOpenSource={onOpenSource} />);

    expect(screen.getByRole("heading", { name: "Current View" })).toBeInTheDocument();
    expect(screen.getByText("v_20260301_01")).toBeInTheDocument();
    expect(screen.getByText("Optical demand is accelerating.")).toBeInTheDocument();
    expect(screen.getByText("20260301 · seq 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View Source" }));
    expect(onOpenSource).toHaveBeenCalledWith("SRC_1");
  });

  it("renders the explicit no-view state", () => {
    render(<ViewTab currentView={null} loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.getByText("No official Current View has been recorded for this Node.")).toBeInTheDocument();
  });
});
