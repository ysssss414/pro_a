import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { getAttribution, mutateAttribution } from "./api/attribution";
import type { AttributionState } from "./api/attribution";
import { WorkbenchError } from "./api/workbench";
import { AttributionReview } from "./components/AttributionReview";

vi.mock("./api/attribution", () => ({ getAttribution: vi.fn(), mutateAttribution: vi.fn() }));
const state: AttributionState = { basis_id: "b".repeat(64), revision: 0, reviewer: "", status: "DRAFT", required: 1, completed: 0,
  claims: [{ candidate_id: "CLM_SYNTHETIC", content: { statement: "Synthetic claim", evidence_excerpt: "Synthetic exact evidence" }, scope: "synthetic scope" }],
  nodes: [{ node_id: "NODE_CREATE", candidate_id: "CAND_CREATE", decision: "CREATE", content: { proposed_name: "Synthetic new Node" } },
    { node_id: "NODE_REUSE", candidate_id: "CAND_REUSE", decision: "REUSE", content: { proposed_name: "Synthetic existing Node" } }],
  decisions: {}, roles: { subject: "Factual subject", context: "Context", related: "Explicit related role" }, audit: [], sidecar: null, qualification: null, receipt: null };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getAttribution).mockResolvedValue(state); vi.mocked(mutateAttribution).mockResolvedValue({}); });
async function mount() { render(<AttributionReview handle="ART_SYNTHETIC" csrf="synthetic-csrf" />); await screen.findByRole("region", { name: "Claim attribution editor" }); }
function choose(outcome: string) {
  fireEvent.change(screen.getByLabelText("Attribution reviewer"), { target: { value: "Synthetic Human" } });
  fireEvent.change(screen.getByLabelText("Attribution outcome"), { target: { value: outcome } });
  fireEvent.change(screen.getByLabelText("Attribution reason"), { target: { value: "Explicit human attribution reason" } });
}
it("shows native evidence without inferred or preselected attribution", async () => {
  await mount(); expect(screen.getByText("Synthetic exact evidence")).toBeVisible();
  expect(screen.getByLabelText("Attribution outcome")).toHaveValue("");
  expect(screen.getByRole("button", { name: "Save attribution" })).toBeDisabled();
  expect(screen.queryByRole("button", { name: /Apply|Promote|Activate/ })).toBeNull();
});
it("requires explicit Node and role selections for MULTI_LINK", async () => {
  await mount(); choose("MULTI_LINK");
  fireEvent.click(screen.getByLabelText(/NODE_CREATE · CREATE/));
  expect(screen.getByLabelText("Role for NODE_CREATE")).toHaveValue("");
  expect(screen.getByRole("button", { name: "Save attribution" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Role for NODE_CREATE"), { target: { value: "subject" } });
  fireEvent.click(screen.getByLabelText(/NODE_REUSE · REUSE/));
  fireEvent.change(screen.getByLabelText("Role for NODE_REUSE"), { target: { value: "context" } });
  fireEvent.click(screen.getByRole("button", { name: "Save attribution" }));
  await waitFor(() => expect(mutateAttribution).toHaveBeenCalledWith("ART_SYNTHETIC", "decisions", expect.objectContaining({ outcome: "MULTI_LINK", scope: "synthetic scope", expected_revision: 0,
    links: [{ node_id: "NODE_CREATE", role: "subject" }, { node_id: "NODE_REUSE", role: "context" }] }), "synthetic-csrf", expect.any(AbortSignal)));
});
it.each(["NO_LINK", "DEFER"])("preserves explicit %s without generated links", async outcome => {
  await mount(); choose(outcome); fireEvent.click(screen.getByRole("button", { name: "Save attribution" }));
  await waitFor(() => expect(mutateAttribution).toHaveBeenCalledWith("ART_SYNTHETIC", "decisions", expect.objectContaining({ outcome, links: [] }), "synthetic-csrf", expect.any(AbortSignal)));
});
it("retains attempted input and explicitly retries a stale attribution against the refreshed revision", async () => {
  await mount(); choose("NO_LINK");
  vi.mocked(getAttribution).mockResolvedValue({ ...state, revision: 1 });
  vi.mocked(mutateAttribution).mockRejectedValueOnce(new WorkbenchError(409, "REVISION_CONFLICT", 1));
  fireEvent.click(screen.getByRole("button", { name: "Save attribution" }));
  await screen.findByText(/This review changed in another tab/);
  expect(screen.getByLabelText("Attribution reason")).toHaveValue("Explicit human attribution reason");
  expect(mutateAttribution).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: "Save attribution" }));
  await waitFor(() => expect(mutateAttribution).toHaveBeenCalledTimes(2));
  expect(vi.mocked(mutateAttribution).mock.calls[1][2]).toMatchObject({ expected_revision: 1 });
});
it("retains an uncertain operation identity for retry", async () => {
  await mount(); choose("LINK");fireEvent.click(screen.getByLabelText(/NODE_CREATE · CREATE/));
  fireEvent.change(screen.getByLabelText("Role for NODE_CREATE"), { target: { value: "subject" } });
  vi.mocked(mutateAttribution).mockRejectedValueOnce(new WorkbenchError(503));
  fireEvent.click(screen.getByRole("button", { name: "Save attribution" }));
  await screen.findByRole("button", { name: "Retry original attribution" });
  fireEvent.click(screen.getByRole("button", { name: "Retry original attribution" }));
  await waitFor(() => expect(mutateAttribution).toHaveBeenCalledTimes(2));
  expect(vi.mocked(mutateAttribution).mock.calls[1][2]).toEqual(vi.mocked(mutateAttribution).mock.calls[0][2]);
});
it("requires separate explicit attribution sealing confirmation", async () => {
  vi.mocked(getAttribution).mockResolvedValue({ ...state, reviewer: "Synthetic Human", completed: 1 });await mount();
  expect(screen.getByRole("button", { name: "Seal attribution sidecar" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Attribution seal reason"), { target: { value: "Explicit separate sidecar seal" } });
  fireEvent.click(screen.getByLabelText("I confirm immutable attribution sealing."));
  fireEvent.click(screen.getByRole("button", { name: "Seal attribution sidecar" }));
  await waitFor(() => expect(mutateAttribution).toHaveBeenCalledWith("ART_SYNTHETIC", "seal", expect.objectContaining({ confirm: true, reason: "Explicit separate sidecar seal" }), "synthetic-csrf", expect.any(AbortSignal)));
});
it("shows exact predicted changes and verifies only an externally registered receipt", async () => {
  vi.mocked(getAttribution).mockResolvedValue({ ...state, status: "SEALED", sidecar: { object_id: "ATTRIBUTION_SYNTHETIC" },
    qualification: { object_id: "OPERATIONAL_SYNTHETIC", adapter_version: "phase42-operational-v1", status: "AWAITING_OPERATOR_ACTION", baseline_sha256: "a".repeat(64), diff_id: "DIFF_SYNTHETIC",
      changes: [{ table: "claim_node_links", key: { claim_id: "CLM_SYNTHETIC", node_id: "NODE_CREATE" } }], tables_touched: ["claim_node_links"], shadow_validation: {}, operator_action: "External operator inspection required." } });
  await mount(); expect(screen.getByRole("heading", { name: "Qualified — External Operator Action Required" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "Save attribution" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Registered execution receipt ID"), { target: { value: "EXECUTION_SYNTHETIC" } });
  fireEvent.click(screen.getByRole("button", { name: "Verify registered execution receipt" }));
  await waitFor(() => expect(mutateAttribution).toHaveBeenCalledWith("ART_SYNTHETIC", "reconcile", { object_id: "EXECUTION_SYNTHETIC" }, "synthetic-csrf", expect.any(AbortSignal)));
  expect(screen.queryByRole("button", { name: /Apply to Production|Promote|Activate/ })).toBeNull();
});
