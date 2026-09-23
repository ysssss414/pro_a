import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { getPacket, getSession, listPackets, loginWorkbench, WorkbenchError } from "./api/workbench";
import type { ReviewPacket } from "./api/workbench";
import { ReviewRoute } from "./components/ReviewRoute";

vi.mock("./api/workbench", async (original) => ({ ...await original<typeof import("./api/workbench")>(),
  getPacket: vi.fn(), getSession: vi.fn(), listPackets: vi.fn(), loginWorkbench: vi.fn(),
}));

const packet: ReviewPacket = {
  artifact_id: "ART_SYNTHETIC", packet_id: "PACKET_SYNTHETIC", run_id: "RUN_SYNTHETIC", mode: "DEMO",
  validation_state: "VALID_BLANK_REVIEW_PACKET", packet_status: "HUMAN_COMPLETION_REQUIRED",
  packet_file_sha256: "a".repeat(64), immutable_packet_sha256: "b".repeat(64),
  source: { source_id: "SRC_SYNTHETIC", source_sha256: "c".repeat(64), source_type: "SYNTHETIC_TEXT", size_bytes: 50 },
  summary: { claims_requiring_decision: 1, nodes_requiring_decision: 1, relations_requiring_decision: 0, aliases_requiring_decision: 0, total_operational_decisions_required: 2 },
  excluded_relation_inventory: { count: 1, candidate_ids: ["REL_EXCLUDED"], policy: "PHASE3E_RELATIONS_EXCLUDED_FROM_PROMOTION", relation_review_reopened: false },
  capabilities: { read_only: true, decision_save_available: false, native_decisions_are_metadata_only: true },
  items: [
    { candidate_id: "CLM_SYNTHETIC", candidate_type: "CLAIM", content_sha256: "d".repeat(64),
      content: { statement: "Synthetic statement.", evidence_pointer: "synthetic:paragraph:1", evidence_excerpt: "Synthetic exact excerpt.",
        evidence_validation: { authoritative_locator: { paragraph: 1, section: "Synthetic section" } } },
      allowed_decisions: ["KEEP", "DROP", "KEEP_NEEDS_REVIEW"], decision_effects: { KEEP_NEEDS_REVIEW: "NON_PROMOTABLE" } },
    { candidate_id: "NODE_SYNTHETIC", candidate_type: "NODE", content_sha256: "e".repeat(64),
      content: { proposed_aliases: ["Synthetic alias"], supporting_evidence: [{ claim_id: "CLM_SYNTHETIC", evidence_excerpt: "Synthetic supporting excerpt." }] },
      allowed_decisions: ["CREATE", "REUSE", "DEFER", "REJECT"], decision_effects: { DEFER: "NO_MUTATION" } },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "DEMO" });
  vi.mocked(listPackets).mockResolvedValue({ packets: [packet] });
  vi.mocked(getPacket).mockResolvedValue(packet);
});

it("shows native identities, counts, evidence, missing metadata and typed capabilities without decision controls", async () => {
  render(<ReviewRoute onAuthenticated={vi.fn()} />);
  expect(await screen.findByText("VALID_BLANK_REVIEW_PACKET")).toBeVisible();
  const identity = screen.getByRole("region", { name: "Packet identity" });
  expect(within(identity).getByText("SRC_SYNTHETIC")).toBeVisible();
  expect(within(identity).getByText("RUN_SYNTHETIC")).toBeVisible();
  expect(screen.getByText("Native items (2)")).toBeVisible();
  expect(screen.getByText("Synthetic exact excerpt.")).toBeVisible();
  expect(screen.getAllByText("Not provided in native packet").length).toBeGreaterThan(0);
  expect(screen.getByText("KEEP · DROP · KEEP_NEEDS_REVIEW")).toBeVisible();
  expect(screen.getByText(/1 excluded functional relations/)).toBeVisible();
  expect(screen.queryByRole("button", { name: /save|approve|reject|seal/i })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "NODE · NODE_SYNTHETIC" }));
  expect(screen.getByText("CREATE · REUSE · DEFER · REJECT")).toBeVisible();
  expect(screen.getAllByText(/Synthetic supporting excerpt/).length).toBeGreaterThan(0);
});

it("requires login, clears the token input and uses only session cookies", async () => {
  vi.mocked(getSession).mockRejectedValueOnce(new WorkbenchError(401));
  render(<ReviewRoute onAuthenticated={vi.fn()} />);
  const input = await screen.findByLabelText("Workbench session token");
  fireEvent.change(input, { target: { value: "synthetic-test-session-token-only-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByText("VALID_BLANK_REVIEW_PACKET");
  expect(loginWorkbench).toHaveBeenCalledWith("synthetic-test-session-token-only-123", expect.any(AbortSignal));
  expect(screen.queryByLabelText("Workbench session token")).toBeNull();
  expect(localStorage.length).toBe(0);
});

it("removes stale packet content when revalidation fails", async () => {
  render(<ReviewRoute onAuthenticated={vi.fn()} />);
  await screen.findByText("VALID_BLANK_REVIEW_PACKET");
  vi.mocked(getPacket).mockRejectedValueOnce(new WorkbenchError(409));
  fireEvent.click(screen.getByRole("button", { name: "Refresh validated packet" }));
  await screen.findByRole("alert");
  expect(screen.queryByText("Synthetic exact excerpt.")).toBeNull();
  expect(screen.queryByRole("region", { name: "Packet identity" })).toBeNull();
});

it("shows an explicit empty registry and aborts outstanding reads on unmount", async () => {
  vi.mocked(listPackets).mockResolvedValue({ packets: [] });
  const view = render(<ReviewRoute onAuthenticated={vi.fn()} />);
  await screen.findByText(/No registered packets/);
  expect(getPacket).not.toHaveBeenCalled();
  const signal = vi.mocked(getSession).mock.calls[0][0];
  view.unmount();
  await waitFor(() => expect(signal.aborted).toBe(true));
});

it("renders source text as text, including HTML-like content", async () => {
  vi.mocked(getPacket).mockResolvedValue({ ...packet, items: [{ ...packet.items[0], content: { evidence_excerpt: '<img src=x onerror="alert(1)">' } }] });
  const view = render(<ReviewRoute onAuthenticated={vi.fn()} />);
  await screen.findByText('<img src=x onerror="alert(1)">');
  expect(view.container.querySelector("img")).toBeNull();
});


it("labels historical lifecycle closure without claiming Workbench review", async () => {
  vi.mocked(getPacket).mockResolvedValue({ ...packet, lifecycle_closure: {
    closure_id: "phase43-stage2-foundation-v1", closure_sha256: "f".repeat(64),
    lifecycle_closed: 274, human_user_qualified: 105, ai_policy_closed: 169,
    followup_governance: 40,
    message: "Historical lifecycle closure is registered; Workbench review completion is not inferred from this total.",
    production_authorized: false,
  }});
  render(<ReviewRoute onAuthenticated={vi.fn()} />);
  const banner = await screen.findByRole("region", { name: "Lifecycle closure status" });
  expect(banner).toHaveTextContent("274 historical items closed");
  expect(banner).toHaveTextContent("Workbench review completion is not inferred from this total");
});
