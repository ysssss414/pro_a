import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { mutateReview, WorkbenchError } from "./api/workbench";
import type { PersistentReview as Review, ReviewPacket } from "./api/workbench";
import { PersistentReview } from "./components/PersistentReview";

vi.mock("./api/workbench", async original => ({ ...await original<typeof import("./api/workbench")>(), mutateReview: vi.fn() }));
const review: Review = { enabled: true, basis_id: "b".repeat(64), review_id: "REVIEW_SYNTHETIC", reviewer: "", revision: 0, status: "DRAFT",
  progress: { total_native_rows: 1, required: 1, completed: 0, remaining: 1, excluded: 1, deferred: 0, nonpromotable: 0, warnings: 0, invalid: 0, dependency_blocked: 0 },
  rows: [{ candidate_id: "CLM_SYNTHETIC", state: null, queues: ["needs_review"], available_decisions: ["KEEP", "DROP", "KEEP_NEEDS_REVIEW"], blocked_decisions: {}, reuse_target: null, undo_event_id: null, decision_effect: null, nonpromotable: false }], audit: [], sealed: null };
const packet: ReviewPacket = { artifact_id: "ART_SYNTHETIC", packet_id: "PACKET_SYNTHETIC", run_id: "RUN_SYNTHETIC", mode: "DEMO",
  validation_state: "VALID_BLANK_REVIEW_PACKET", packet_status: "HUMAN_COMPLETION_REQUIRED", packet_file_sha256: "a".repeat(64), immutable_packet_sha256: "b".repeat(64),
  source: { source_id: "SRC_SYNTHETIC", source_sha256: "c".repeat(64), source_type: "SYNTHETIC_TEXT", size_bytes: 10 }, summary: {},
  excluded_relation_inventory: { count: 1, candidate_ids: ["REL_EXCLUDED"], policy: "AUDIT_ONLY", relation_review_reopened: false },
  capabilities: { read_only: false, decision_save_available: true, native_decisions_are_metadata_only: true }, review,
  items: [{ candidate_id: "CLM_SYNTHETIC", candidate_type: "CLAIM", content_sha256: "d".repeat(64), content: { evidence_excerpt: "Synthetic evidence", recommended_decision: "KEEP" }, allowed_decisions: ["KEEP", "DROP", "KEEP_NEEDS_REVIEW"], decision_effects: {} }] };
const refresh = vi.fn();
beforeEach(() => { vi.resetAllMocks(); refresh.mockResolvedValue(packet); vi.mocked(mutateReview).mockResolvedValue({ revision: 1 }); });
function mount(value = review) { return render(<PersistentReview packet={packet} review={value} csrf="synthetic-csrf" refresh={refresh} />); }
function input() {
  fireEvent.change(screen.getByLabelText("Reviewer"), { target: { value: "Synthetic Human" } });
  fireEvent.change(screen.getByLabelText("Decision"), { target: { value: "KEEP_NEEDS_REVIEW" } });
  fireEvent.change(screen.getByLabelText("Decision reason"), { target: { value: "Explicit human evidence assessment" } });
}
it("does not prefill advice and keeps excluded rows outside the editor", () => {
  mount(); expect(screen.getByLabelText("Decision")).toHaveValue(""); expect(screen.getByLabelText("Decision reason")).toHaveValue("");
  expect(screen.getByRole("button", { name: "Save decision" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Review queue"), { target: { value: "excluded" } });
  expect(screen.getByText(/REL_EXCLUDED/)).toBeVisible(); expect(screen.queryByLabelText("Decision")).toBeNull();
});
it("submits explicit native input with revision, basis, reviewer and CSRF", async () => {
  mount(); input(); fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  expect(mutateReview).toHaveBeenCalledWith("ART_SYNTHETIC", "decisions", expect.objectContaining({ expected_revision: 0, basis_id: review.basis_id,
    reviewer: "Synthetic Human", decision: "KEEP_NEEDS_REVIEW", reason: "Explicit human evidence assessment", target_node_id: "", operation_id: expect.any(String) }), "synthetic-csrf", expect.any(AbortSignal));
});
it("preserves attempted input on conflict and requires an explicit retry with refreshed revision", async () => {
  vi.mocked(mutateReview).mockRejectedValueOnce(new WorkbenchError(409, "REVISION_CONFLICT", 1));
  const view = mount(); input(); fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  await screen.findByRole("button", { name: "Retry with refreshed revision" });
  expect(screen.getByLabelText("Decision reason")).toHaveValue("Explicit human evidence assessment");
  view.rerender(<PersistentReview packet={packet} review={{ ...review, revision: 1 }} csrf="synthetic-csrf" refresh={refresh} />);
  expect(mutateReview).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Retry with refreshed revision" }));
  await waitFor(() => expect(mutateReview).toHaveBeenCalledTimes(2));
  const calls = vi.mocked(mutateReview).mock.calls;
  expect(calls[1][2]).toMatchObject({ expected_revision: 1 });
  expect(calls[1][2]).not.toMatchObject({ operation_id: (calls[0][2] as { operation_id: string }).operation_id });
});
it.each([new TypeError("lost response"), new WorkbenchError(503)])("retries an uncertain save with the original identity", async error => {
  vi.mocked(mutateReview).mockRejectedValueOnce(error); mount(); input(); fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  await screen.findByRole("button", { name: "Retry original operation" });
  expect(screen.getByLabelText("Decision reason")).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Retry original operation" }));
  await waitFor(() => expect(mutateReview).toHaveBeenCalledTimes(2));
  expect(vi.mocked(mutateReview).mock.calls[1][2]).toEqual(vi.mocked(mutateReview).mock.calls[0][2]);
});
it("sends a bounded undo event and an explicit undo reason", async () => {
  mount({ ...review, reviewer: "Synthetic Human", revision: 2, rows: [{ ...review.rows[0], undo_event_id: 7 }] });
  fireEvent.change(screen.getByLabelText("Undo reason"), { target: { value: "Reconsider latest save" } });
  fireEvent.click(screen.getByRole("button", { name: "Undo last Save" }));
  await waitFor(() => expect(mutateReview).toHaveBeenCalledWith("ART_SYNTHETIC", "undo", expect.objectContaining({ event_id: 7, expected_revision: 2, reason: "Reconsider latest save" }), "synthetic-csrf", expect.any(AbortSignal)));
});
it("requires native validation and explicit seal confirmation; an uncertain seal keeps its identity", async () => {
  vi.mocked(mutateReview).mockResolvedValueOnce({ revision: 3 }).mockRejectedValueOnce(new WorkbenchError(503)).mockResolvedValueOnce({ revision: 4 });
  mount({ ...review, reviewer: "Synthetic Human", revision: 3 });
  fireEvent.click(screen.getByRole("button", { name: "Validate completion" }));
  await screen.findByRole("region", { name: "Seal confirmation" });
  expect(screen.getByRole("button", { name: "Confirm seal" })).toBeDisabled();
  expect(screen.getByText(/Sealing does not modify Production/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Seal reason"), { target: { value: "Explicit review-only seal" } });
  fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(screen.getByRole("button", { name: "Confirm seal" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Confirm seal" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Confirm seal" }));
  await waitFor(() => expect(mutateReview).toHaveBeenCalledTimes(3));
  expect(vi.mocked(mutateReview).mock.calls[2][2]).toEqual(vi.mocked(mutateReview).mock.calls[1][2]);
});
it("renders sealed results without mutation controls", () => {
  mount({ ...review, status: "SEALED", reviewer: "Synthetic Human", sealed: { objects: [], validation: { status: "VALID" }, production_authorized: false, qualification_created: false } });
  expect(screen.getByRole("region", { name: "Sealed review result" })).toBeVisible();
  expect(screen.queryByRole("button", { name: /Save decision|Undo last Save|Validate completion|Confirm seal/ })).toBeNull();
});
