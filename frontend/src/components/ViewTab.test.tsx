import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentViewCompare } from "../api/client";
import type { CurrentViewCompareResult, CurrentViewResult } from "../api/types";
import { ViewTab } from "./ViewTab";

vi.mock("../api/client", () => ({ getCurrentViewCompare: vi.fn() }));

const currentView: CurrentViewResult = {
  view_id: "VIEW_1",
  node_id: "NODE_EML",
  version: "v_20260301_01",
  status: "official",
  change_level: "initial",
  previous_view_id: null,
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

const compareResult: CurrentViewCompareResult = {
  node_id: "NODE_EML",
  base: {
    view_id: "VIEW_OLD",
    version: "v_20260215",
    revision_date: "20260215",
    revision_seq: 0,
    change_level: "initial",
  },
  target: {
    view_id: "VIEW_LATEST",
    version: "v_20260301",
    revision_date: "20260301",
    revision_seq: 0,
    change_level: "material",
    previous_view_id: "VIEW_OLD",
    recent_change: "Stored official change.",
  },
  scalar_changes: [
    { field: "one_line_conclusion", changed: true, before: "Old conclusion.", after: "New conclusion." },
    { field: "investment_implication", changed: false, before: "Same.", after: "Same." },
  ],
  list_changes: {
    key_facts: { added: ["New fact."], removed: ["Old fact."], unchanged: [] },
    key_watch_items: { added: [], removed: [], unchanged: ["Watch."] },
  },
  type_specific_changes: {
    demand_drivers: {
      status: "changed",
      kind: "list",
      added: ["New demand driver."],
      removed: [],
      unchanged: ["Existing demand driver."],
    },
  },
  evidence: {
    added: [{
      claim_id: "CLAIM_RAW_ADDED",
      resolved: true,
      statement: "Resolved evidence statement.",
      status: "current",
      confidence: 0.8,
      source_id: "SRC_1",
      source_title: "Source title",
      source_rank: "A",
    }],
    removed: [{
      claim_id: "CLAIM_RAW_REMOVED",
      resolved: false,
      statement: null,
      status: null,
      confidence: null,
      source_id: null,
      source_title: null,
      source_rank: null,
    }],
    unchanged: [],
  },
  trigger_source_change: { status: "changed", before: "SRC_OLD", after: "SRC_NEW" },
  has_changes: true,
};

describe("ViewTab", () => {
  beforeEach(() => {
    vi.mocked(getCurrentViewCompare).mockReset();
  });

  it("renders the Current View content, version, revision, and Source action", () => {
    const onOpenSource = vi.fn();
    render(<ViewTab currentViews={[currentView]} loading={false} error={null} onOpenSource={onOpenSource} />);

    expect(screen.getByRole("heading", { name: "Current View" })).toBeInTheDocument();
    expect(screen.getByText("Initial View")).toBeInTheDocument();
    expect(screen.getByText("No previous revision to compare")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Compare with previous" })).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "View version" })).not.toBeInTheDocument();
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
    render(<ViewTab currentViews={[view]} primaryType="Company" loading={false} error={null} onOpenSource={vi.fn()} />);
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
    render(<ViewTab currentViews={[view]} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />);
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
    render(<ViewTab currentViews={[view]} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.getAllByText(/2026年7月和8月MLCC单月价格环比均上涨30%以上/)).toHaveLength(1);
    expect(screen.queryByText("关键变化")).not.toBeInTheDocument();
  });

  it("navigates versions with the shared Product presentation and resets on Node change", () => {
    const oldView: CurrentViewResult = {
      ...currentView,
      view_id: "VIEW_OLD",
      version: "v_20260215",
      content_json: {
        one_line_conclusion: "Old Product conclusion.",
        key_facts: ["Old Product fact."],
        type_specific: { demand_drivers: ["Old demand driver."] },
      },
      trigger_claim_ids: ["CLAIM_OLD"],
      revision_date: "20260215",
    };
    const latestView: CurrentViewResult = {
      ...currentView,
      view_id: "VIEW_LATEST",
      version: "v_20260301",
      change_level: "material",
      previous_view_id: "VIEW_OLD",
      content_json: {
        one_line_conclusion: "Latest Product conclusion.",
        key_facts: ["Latest Product fact."],
        type_specific: { demand_drivers: ["Latest demand driver."] },
      },
      trigger_claim_ids: ["CLAIM_LATEST"],
      revision_date: "20260301",
    };

    const { rerender } = render(
      <ViewTab currentViews={[latestView, oldView]} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />,
    );
    expect(screen.getByText("Latest Product conclusion.")).toBeInTheDocument();
    expect(screen.getByText(/需求驱动: Latest demand driver./)).toBeInTheDocument();
    expect(screen.getByText("1 primary Claims")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("combobox", { name: "View version" }), {
      target: { value: "VIEW_OLD" },
    });
    expect(screen.getByText("Old Product conclusion.")).toBeInTheDocument();
    expect(screen.getByText(/需求驱动: Old demand driver./)).toBeInTheDocument();
    expect(screen.queryByText("Latest Product conclusion.")).not.toBeInTheDocument();
    expect(screen.queryByText("CLAIM_OLD")).not.toBeInTheDocument();

    const nextNodeView: CurrentViewResult = {
      ...latestView,
      view_id: "VIEW_NEXT_NODE",
      node_id: "NODE_NEXT",
      version: "v_20260401",
      previous_view_id: null,
      content_json: { one_line_conclusion: "Next Node conclusion." },
    };
    rerender(
      <ViewTab currentViews={[nextNodeView]} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />,
    );
    expect(screen.getByText("Next Node conclusion.")).toBeInTheDocument();
    expect(screen.queryByText("Old Product conclusion.")).not.toBeInTheDocument();
  });

  it("compares Product versions with exact deltas and clears compare state on Node change", async () => {
    vi.mocked(getCurrentViewCompare).mockResolvedValue(compareResult);
    const oldView: CurrentViewResult = {
      ...currentView,
      view_id: "VIEW_OLD",
      version: "v_20260215",
      revision_date: "20260215",
    };
    const latestView: CurrentViewResult = {
      ...currentView,
      view_id: "VIEW_LATEST",
      version: "v_20260301",
      previous_view_id: "VIEW_OLD",
      revision_date: "20260301",
    };
    const history = [latestView, oldView];
    const { rerender } = render(
      <ViewTab currentViews={history} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Compare with previous" }));
    expect(await screen.findByRole("heading", { name: "Current View Compare" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "BASE version" })).toHaveValue("VIEW_OLD");
    expect(screen.getByRole("combobox", { name: "TARGET version" })).toHaveValue("VIEW_LATEST");
    expect(screen.getByText("v_20260215 → v_20260301")).toBeInTheDocument();
    expect(screen.getByText("Old conclusion.")).toBeInTheDocument();
    expect(screen.getByText("New conclusion.")).toBeInTheDocument();
    expect(screen.getByText("New fact.")).toBeInTheDocument();
    expect(screen.getByText("Old fact.")).toBeInTheDocument();
    expect(screen.getByText("需求驱动")).toBeInTheDocument();
    expect(screen.queryByText("demand_drivers")).not.toBeInTheDocument();
    expect(screen.getByText("新增证据 1 条")).toBeInTheDocument();
    expect(screen.getByText("移除证据 1 条")).toBeInTheDocument();
    expect(screen.getByText("Resolved evidence statement.")).toBeInTheDocument();
    expect(screen.queryByText("CLAIM_RAW_ADDED")).not.toBeInTheDocument();
    expect(screen.queryByText("CLAIM_RAW_REMOVED")).not.toBeInTheDocument();
    expect(getCurrentViewCompare).toHaveBeenCalledWith(
      "NODE_EML", "VIEW_OLD", "VIEW_LATEST", expect.any(AbortSignal),
    );

    const nextNodeView = {
      ...currentView,
      node_id: "NODE_NEXT",
      view_id: "VIEW_NEXT",
      previous_view_id: null,
      content_json: { one_line_conclusion: "Next node normal View." },
    };
    rerender(<ViewTab currentViews={[nextNodeView]} primaryType="Product" loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(await screen.findByText("Next node normal View.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Current View Compare" })).not.toBeInTheDocument();
    expect(getCurrentViewCompare).toHaveBeenCalledTimes(1);
  });

  it("uses the Company compare label and exits safely after an API failure", async () => {
    let rejectCompare: (reason: Error) => void = () => undefined;
    vi.mocked(getCurrentViewCompare).mockImplementation(() => new Promise((_, reject) => {
      rejectCompare = reject;
    }));
    const oldView = { ...currentView, view_id: "VIEW_OLD", version: "v_old" };
    const latestView = {
      ...currentView,
      view_id: "VIEW_LATEST",
      version: "v_new",
      previous_view_id: "VIEW_OLD",
      content_json: { one_line_conclusion: "Normal Company View.", key_facts: ["Company progress."] },
    };
    render(
      <ViewTab currentViews={[latestView, oldView]} primaryType="Company" loading={false} error={null} onOpenSource={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Compare with previous" }));
    await waitFor(() => expect(getCurrentViewCompare).toHaveBeenCalledOnce());
    await act(async () => { rejectCompare(new Error("API failed")); });
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load Current View comparison.");
    fireEvent.click(screen.getByRole("button", { name: "Exit Compare" }));
    expect(screen.getByText("Normal Company View.")).toBeInTheDocument();
    expect(screen.getByText("关键进展")).toBeInTheDocument();
  });

  it("renders the explicit no-view state", () => {
    render(<ViewTab currentViews={[]} loading={false} error={null} onOpenSource={vi.fn()} />);
    expect(screen.getByText("No official Current View has been recorded for this Node.")).toBeInTheDocument();
  });
});
