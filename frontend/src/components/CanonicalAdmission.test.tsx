import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../api/workbench";
import { CanonicalAdmission } from "./CanonicalAdmission";

vi.mock("../api/workbench", () => ({ request: vi.fn() }));
beforeEach(() => vi.mocked(request).mockReset());
const plan = { object_id: "ADMISSION_test", envelope_id: "OPERATIONAL_test", diff_id: "DIFF_test",
  changes: [{ table: "claims", action: "INSERT", key: { claim_id: "CLM_test" }, values: { statement: "Source assertion", evidence: "Exact words", reality_support: "UNVERIFIED" }, withheld_columns: [{ column: "metadata_json", sha256: "a".repeat(64) }] }],
  insert_counts: { claims: 1 }, unchanged_count: 2, evidence: { pointer: "PAGE:1" }, excluded: [{ decision: "DROP" }],
  native_items: [], attribution_items: [{ claim_id: "CLM_test", outcome: "NO_LINK", reason: "Unresolved subject" }],
  pre_state_sha256: "pre", post_state_sha256: "post", governance: "SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY" };
const prepared = { status: "AWAITING_SECOND_APPROVAL", plan };
const pending = { ...prepared, status: "AUTHORIZED_PENDING_OPERATOR", approval: { object_id: "APPROVAL_test" } };

it("qualifies sealed P1, displays exact diff and authorizes only the frozen SHA once", async () => {
  vi.mocked(request).mockResolvedValueOnce({ status: "QUALIFICATION_REQUIRED", plan: null }).mockResolvedValueOnce(prepared)
    .mockResolvedValue(pending);
  render(<CanonicalAdmission handle="ART_test" csrf="csrf-test" />);
  const button = await screen.findByRole("button", { name: "确认本次 Canonical 正式入库" });
  expect(button).toBeDisabled();
  expect(screen.getByText("claims · INSERT")).toBeVisible();
  expect(screen.getByText(/metadata_json:/)).toBeVisible();
  expect(screen.getByText(/尚无归属/)).toBeVisible();
  fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(button);
  await screen.findByText("AUTHORIZED_PENDING_OPERATOR");
  expect(screen.queryByRole("button", { name: "确认本次 Canonical 正式入库" })).not.toBeInTheDocument();
  const writes = vi.mocked(request).mock.calls.filter(c => c[0].endsWith("/approval"));
  expect(writes).toHaveLength(1);
  expect(JSON.parse(writes[0][2]!.body as string)).toEqual({ proposal_id: "ADMISSION_test", confirm: true });
  expect(vi.mocked(request).mock.calls.every(c => !/execute|grant|operator/.test(c[0]))).toBe(true);
});

it("reads durable approval after a lost response without a second write", async () => {
  vi.mocked(request).mockResolvedValueOnce(prepared).mockRejectedValueOnce(new Error("response lost")).mockResolvedValue(pending);
  render(<CanonicalAdmission handle="ART_test" csrf="csrf-test" />);
  const button = await screen.findByRole("button", { name: "确认本次 Canonical 正式入库" });
  fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(button);
  await screen.findByText("AUTHORIZED_PENDING_OPERATOR");
  expect(vi.mocked(request).mock.calls.filter(c => c[0].endsWith("/approval"))).toHaveLength(1);
});

it("restores a reconciled receipt on remount without showing pending execution", async () => {
  vi.mocked(request).mockResolvedValue({ ...pending, status: "RECONCILED", receipt: { object_id: "EXECUTION_test", actual_mutation_counts: { claims: 1 } } });
  const first = render(<CanonicalAdmission handle="ART_test" csrf="csrf-test" />);
  await screen.findByText("RECONCILED"); first.unmount();
  render(<CanonicalAdmission handle="ART_test" csrf="new-session" />);
  await screen.findByText("RECONCILED");
  await waitFor(() => expect(screen.queryByRole("checkbox")).not.toBeInTheDocument());
  expect(vi.mocked(request).mock.calls.every(c => !c[2]?.method)).toBe(true);
});
