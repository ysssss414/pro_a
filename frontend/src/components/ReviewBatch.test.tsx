import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../api/workbench";
import { ReviewBatch } from "./ReviewBatch";

vi.mock("../api/workbench", () => ({ request: vi.fn() }));
beforeEach(() => { vi.mocked(request).mockReset(); window.history.replaceState(null, "", "/"); });
const id = "a".repeat(64);
const proposal = { proposal_id: id, approved: false, binding_matches: true, current_revision: 0,
  counts: { KEEP: 1 }, status: "DRAFT", evidence: [{ statement: "Synthetic evidence" }],
  advice: { A: { items: [{ candidate_id: "C1", judgment: "SUPPORTED", reason: "Inspected" }] },
            B: { items: [{ candidate_id: "C1", judgment: "SUPPORTED", reason: "Independently inspected" }] } },
  proposal: { kind: "native", binding: {}, expected_revision: 0, reason: "Checked all evidence",
              items: [{ candidate_id: "C1", decision: "KEEP", reason: "Supported" }] } };

it("approves only the displayed frozen hash after explicit confirmation", async () => {
  vi.mocked(request).mockResolvedValueOnce(proposal).mockResolvedValueOnce({ status: "SEALED", result: {} });
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(<ReviewBatch handle="ART_SYNTHETIC" csrf="synthetic-csrf" refresh={refresh} />);
  fireEvent.change(screen.getByLabelText("Proposal SHA-256"), { target: { value: id } });
  fireEvent.click(screen.getByText("查看冻结方案"));
  const approve = await screen.findByRole("button", { name: "批准整批并 Seal" });
  expect(approve).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(approve);
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  const options = vi.mocked(request).mock.calls[1][2]!;
  expect(JSON.parse(options.body as string)).toEqual({ proposal_id: id, confirm: true });
  expect(options.headers).toEqual({ "Content-Type": "application/json", "X-CSRF-Token": "synthetic-csrf" });
  fireEvent.change(screen.getByLabelText("Proposal SHA-256"), { target: { value: "b".repeat(64) } });
  expect(screen.queryByRole("button", { name: "批准整批并 Seal" })).not.toBeInTheDocument();
});

it("blocks an identity drift and shows the submitted evidence without HTML execution", async () => {
  vi.mocked(request).mockResolvedValue({ ...proposal, binding_matches: false,
    evidence: { statement: '<img src=x onerror="alert(1)">' } });
  render(<ReviewBatch handle="ART_SYNTHETIC" csrf="synthetic-csrf" refresh={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Proposal SHA-256"), { target: { value: id } });
  fireEvent.click(screen.getByText("查看冻结方案"));
  expect(await screen.findByRole("alert")).toHaveTextContent("禁止批准");
  expect(screen.getByRole("checkbox")).toBeDisabled();
  expect(document.querySelector("img")).toBeNull();
});
