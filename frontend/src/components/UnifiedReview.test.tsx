import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../api/workbench";
import { UnifiedReview } from "./UnifiedReview";

vi.mock("../api/workbench", () => ({ request: vi.fn() }));
beforeEach(() => vi.mocked(request).mockReset());
const id = "a".repeat(64);
const row = { candidate_id: "C1", candidate_type: "CLAIM", content_sha256: "b".repeat(64), allowed_decisions: ["KEEP", "DROP", "KEEP_NEEDS_REVIEW"], content: { statement: "匿名公司线索", evidence_excerpt: "Exact source words" } };
const context = { binding: {}, revision: 0, status: "DRAFT", candidates: [row], advice: { A: { items: [{ candidate_id: "C1", judgment: "SUPPORTED", reason: "Source assertion only" }] } }, approved_proposal_id: null, proposal_ids: [] };
const universe = { claims: { C1: { scope: "anonymous" } }, nodes: {} };
const preview = { binding: {}, revision: 0, universe, universe_sha256: "c".repeat(64) };
const proposal = { proposal_id: id, approved: false, status: "PREPARED", result: null, proposal: { native_items: [{ candidate_id: "C1", content_sha256: row.content_sha256, decision: "KEEP", target_node_id: "", reason: "Checked" }], attribution_items: [], reason: "Explicit human review", universe, binding: {}, expected_revision: 0, universe_sha256: "c".repeat(64) } };

async function native() {
  await screen.findByText("A: SUPPORTED · Source assertion only");
  fireEvent.change(screen.getByLabelText("Native decision"), { target: { value: "KEEP" } });
  fireEvent.change(screen.getByLabelText("Native reason"), { target: { value: "Source wording checked" } });
  fireEvent.click(screen.getByRole("button", { name: "预验证 Native 并建立归属候选" }));
  await screen.findByLabelText("Attribution outcome");
}

it("edits both decisions then sends one approval of the frozen identity", async () => {
  vi.mocked(request).mockResolvedValueOnce(context).mockResolvedValueOnce(preview).mockResolvedValueOnce(proposal)
    .mockResolvedValueOnce({ ...proposal, approved: true, status: "APPROVED", progress: { stage: "native", completed_steps: 1, total_steps: 2 } })
    .mockResolvedValueOnce({ ...proposal, approved: true, status: "SEALED", result: { attribution_id: "ATTRIBUTION_test" } });
  render(<UnifiedReview handle="ART_TEST" csrf="csrf-test" />);
  await native();
  fireEvent.change(screen.getByLabelText("Attribution outcome"), { target: { value: "NO_LINK" } });
  fireEvent.change(screen.getByLabelText("Attribution reason"), { target: { value: "Do not infer anonymous company" } });
  fireEvent.change(screen.getByLabelText("整份方案审核理由"), { target: { value: "Explicit human review" } });
  fireEvent.click(screen.getByRole("button", { name: "验证并冻结完整方案" }));
  const approve = await screen.findByRole("button", { name: "一次批准 Native + Attribution" });
  expect(approve).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(approve);
  await screen.findByText(/一次人工批准已完成 Native Seal/);
  const calls = vi.mocked(request).mock.calls.filter(c => c[0].endsWith("/approval"));
  expect(calls).toHaveLength(2); // One human confirmation, same approved identity continued by the machine.
  expect(calls[0][2]!.body).toBe(calls[1][2]!.body);
  expect(JSON.parse(calls[0][2]!.body as string)).toEqual({ proposal_id: id, confirm: true });
  expect(calls[0][2]!.headers).toEqual({ "Content-Type": "application/json", "X-CSRF-Token": "csrf-test" });
});

it("invalidates dependent attribution when the Native decision changes", async () => {
  vi.mocked(request).mockResolvedValueOnce(context).mockResolvedValueOnce(preview);
  render(<UnifiedReview handle="ART_TEST" csrf="csrf-test" />);
  await native();
  fireEvent.change(screen.getByLabelText("Attribution outcome"), { target: { value: "DEFER" } });
  fireEvent.change(screen.getByLabelText("Native decision"), { target: { value: "KEEP_NEEDS_REVIEW" } });
  expect(screen.queryByLabelText("Attribution outcome")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "验证并冻结完整方案" })).toBeDisabled();
});

it("reloads durable approval after lost response and resumes the same hash", async () => {
  vi.mocked(request).mockResolvedValueOnce({ ...context, approved_proposal_id: id }).mockResolvedValueOnce({ ...proposal, approved: true, status: "APPROVED" })
    .mockRejectedValueOnce(new Error("Interrupted"))
    .mockResolvedValueOnce({ ...proposal, approved: true, status: "APPROVED" });
  render(<UnifiedReview handle="ART_TEST" csrf="csrf-test" />);
  const resume = await screen.findByRole("button", { name: "恢复同一已批准方案" });
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await waitFor(() => expect(resume).not.toBeDisabled()); fireEvent.click(resume);
  await screen.findByRole("alert");
  expect(vi.mocked(request).mock.calls[3][0]).toBe(`/reviews/ART_TEST/unified/proposals/${id}`);
  expect(screen.getByLabelText("Native decision")).toBeDisabled();
});
