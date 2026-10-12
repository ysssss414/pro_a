import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../api/workbench";
import { CandidateRange } from "./CandidateRange";
import { CandidateAdvice } from "./CandidateAdvice";

vi.mock("../api/workbench", () => ({ request: vi.fn() }));
beforeEach(() => vi.mocked(request).mockReset());

it("submits the selected Unicode codepoint range with the immutable input identity", async () => {
  vi.mocked(request).mockResolvedValueOnce({ attempts: [{ attempt_id: "ATT_SYNTHETIC", identity: "sha-synthetic",
    claims: [{ observation_id: "OBS_SYNTHETIC", statement: "Synthetic statement", status: "ISOLATED", errors: [] }],
    evidence: [{ evidence_ref: "EV_SYNTHETIC", source_start: 10, source_end: 16, text: "😀预\n计增长", locator: "PAGE:1" }] }] })
    .mockResolvedValueOnce({ run: {} });
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(<CandidateRange runId="RUN_SYNTHETIC" csrf="csrf-synthetic" refresh={refresh} />);
  fireEvent.click(screen.getByText("Correct an Evidence range"));
  fireEvent.click(screen.getByRole("button", { name: "Load candidate ranges" }));
  fireEvent.change(await screen.findByLabelText("Claim"), { target: { value: "OBS_SYNTHETIC" } });
  fireEvent.change(screen.getByLabelText("Evidence unit"), { target: { value: "EV_SYNTHETIC" } });
  const text = screen.getByLabelText("Select the original range") as HTMLTextAreaElement;
  text.setSelectionRange(2, 5);
  fireEvent.select(text);
  fireEvent.change(screen.getByLabelText("Revision reason"), { target: { value: "Original line break checked" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit exact range for new review" }));
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  const options = vi.mocked(request).mock.calls[1][2]!;
  expect(options.headers).toEqual({ "Content-Type": "application/json", "X-CSRF-Token": "csrf-synthetic" });
  expect(JSON.parse(options.body as string)).toMatchObject({ input_identity: "sha-synthetic",
    observation_id: "OBS_SYNTHETIC", evidence_ref: "EV_SYNTHETIC", source_start: 11, source_end: 14 });
});

it("imports one actual opinion without generating the other reviewer or Human approval", async () => {
  vi.mocked(request).mockResolvedValue({ slot: "A", reviewer_id: "synthetic-reviewer-A" });
  render(<CandidateAdvice handle="ART_SYNTHETIC" csrf="csrf-synthetic" />);
  const opinion = { slot: "A", reviewer_id: "synthetic-reviewer-A", reviewer_type: "MODEL",
    context_sha256: "a".repeat(64), items: [] };
  const file = new File([JSON.stringify(opinion)], "synthetic-advice.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => JSON.stringify(opinion) });
  fireEvent.change(screen.getByLabelText("Import one actual reviewer opinion (JSON)"), { target: { files: [file] } });
  expect(await screen.findByRole("status")).toHaveTextContent("Human decisions and Seal are still required");
  expect(request).toHaveBeenCalledOnce();
  expect(JSON.parse(vi.mocked(request).mock.calls[0][2]!.body as string)).toEqual(opinion);
});
