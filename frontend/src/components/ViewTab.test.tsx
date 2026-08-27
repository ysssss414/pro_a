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
  content_json: {
    one_line_conclusion: "Optical demand is accelerating.",
    key_facts: ["Optical demand is accelerating."],
    investment_implication: "Capacity expansion is supported.",
    key_watch_items: ["Track deployment."],
    core_disagreements: ["Independent validation remains limited."],
    type_specific: {},
  },
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
    expect(screen.getAllByText("Optical demand is accelerating.")).toHaveLength(2);
    expect(screen.getByText("投资含义")).toBeInTheDocument();
    expect(screen.getByText("证据边界")).toBeInTheDocument();
    expect(screen.queryByText("CLAIM_1")).not.toBeInTheDocument();
    expect(screen.getByText("Revision date")).toBeInTheDocument();
    expect(screen.getByText("20260301")).toBeInTheDocument();
    expect(screen.queryByText("seq 1")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View Source" }));
    expect(onOpenSource).toHaveBeenCalledWith("SRC_1");
  });

  it("uses the Company template and hides initial recent change", () => {
    const view = { ...currentView, previous_view_id: null, content_json: {
      one_line_conclusion: "昀冢科技处于扩产阶段。",
      key_facts: ["一期产线出货。", "二期扩产。"],
      core_logic: ["一期产线出货。", "二期扩产。"],
      investment_implication: "未来规模有提升空间。",
      key_watch_items: ["跟踪兑现。"],
      recent_change: "首次建立 official Current View。",
      major_risks: ["公司指引仍需验证。"],
      type_specific: {},
    }};
    render(<ViewTab currentView={view} primaryType="Company" loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.getByText("关键进展")).toBeInTheDocument();
    expect(screen.queryByText("最近变化")).not.toBeInTheDocument();
    expect(screen.getAllByText("一期产线出货。")).toHaveLength(1);
  });

  it("deduplicates Product dimensions and hides empty dimensions", () => {
    const view = { ...currentView, content_json: {
      one_line_conclusion: "MLCC价格改善。",
      key_facts: ["MLCC库存下降。"],
      investment_implication: "等待更多验证。",
      key_watch_items: ["跟踪价格。"],
      core_disagreements: ["来源单一。"],
      type_specific: {
        demand_drivers: ["AI需求形成挤出效应。"],
        pricing: ["MLCC库存下降。"],
        applications: [],
        supply_capacity: [],
        product_evolution: [],
      },
    }};
    render(<ViewTab currentView={view} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.queryByText(/pricing:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/applications:/)).not.toBeInTheDocument();
    expect(screen.getByText(/需求驱动: AI需求形成挤出效应。/)).toBeInTheDocument();
    expect(screen.queryByText(/demand_drivers/)).not.toBeInTheDocument();
    expect(screen.getByText("关键变化")).toBeInTheDocument();
  });

  it("deduplicates the canonical MLCC price statement at presentation time", () => {
    const view = { ...currentView, content_json: {
      one_line_conclusion: "据现有财通证券业绩会更新材料，2026年7月和8月MLCC单月价格环比均上涨30%以上；周期判断仍需验证。",
      key_facts: ["据该材料，2026年7月和8月MLCC单月价格环比均上涨30%以上。"],
      investment_implication: "价格端改善仍需验证。",
      key_watch_items: ["跟踪价格。"],
      core_disagreements: ["来源单一。"],
      type_specific: {
        demand_drivers: ["AI需求形成挤出效应。"],
        pricing: ["据该材料，2026年7月和8月MLCC单月价格环比均上涨30%以上。"],
      },
    }};
    render(<ViewTab currentView={view} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.getAllByText(/2026年7月和8月MLCC单月价格环比均上涨30%以上/)).toHaveLength(1);
    expect(screen.queryByText("关键变化")).not.toBeInTheDocument();
  });

  it("renders the explicit no-view state", () => {
    render(<ViewTab currentView={null} loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.getByText("No official Current View has been recorded for this Node.")).toBeInTheDocument();
  });
});
