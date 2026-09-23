import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getCloudJob, getCloudJobArtifacts, getCloudJobEvents, listCloudJobs, submitCloudJob,
  type CloudJob,
} from "../api/cloudJobs";
import { getSession, listPackets, loginWorkbench, WorkbenchError } from "../api/workbench";
import { CloudJobsWorkbench } from "./CloudJobsWorkbench";

vi.mock("../api/cloudJobs", () => ({
  getCloudJob: vi.fn(), getCloudJobArtifacts: vi.fn(), getCloudJobEvents: vi.fn(),
  listCloudJobs: vi.fn(), submitCloudJob: vi.fn(),
}));
vi.mock("../api/workbench", async (original) => {
  const actual = await original<typeof import("../api/workbench")>();
  return { ...actual, getSession: vi.fn(), listPackets: vi.fn(), loginWorkbench: vi.fn() };
});

function job(status: CloudJob["status"] = "SUCCEEDED", id = "JOB_EXACT"): CloudJob {
  return {
    job_id: id, operation_kind: "SEMANTIC_DECOMPOSITION",
    input: { artifact_id: "ART_" + "a".repeat(32), sha256: "b".repeat(64), source_id: "SRC_SYNTHETIC" },
    status, phase: status === "RUNNING" ? "CALL_POSSIBLE" : status === "QUEUED" ? "QUEUED" : "TERMINAL",
    provider: "DETERMINISTIC_FAKE", requested_model: "fake-semantic-v1",
    provider_reported_model: status === "QUEUED" ? null : "fake-semantic-v1",
    provider_request_id: status === "QUEUED" ? null : "FAKE_REQ_0001",
    model_identity_status: status === "QUEUED" ? null : "EXACT",
    provider_adapter_version: "deterministic-fake-v1",
    runtime_identity: { git_sha: "abc123", cloud_contract_version: "cloud-inference-v1" },
    prompt_identity: { prompt_id: "semantic-decomposition", prompt_version: "2.1" },
    configuration_identity: { configuration_sha256: "e".repeat(64) },
    retry_owner: "DURABLE_CLOUD_WORKER", attempt_count: status === "QUEUED" ? 0 : 1,
    budget: { max_calls: 2, max_attempts: 2, max_output_tokens: 8192, max_total_tokens: 20000, reserved_calls: 0, reserved_tokens: 0 },
    usage: status === "QUEUED" ? { status: "UNKNOWN", input_tokens: null, output_tokens: null, total_tokens: null, cached_tokens: null }
      : { status: "KNOWN", input_tokens: 100, output_tokens: 20, total_tokens: 120, cached_tokens: 5 },
    validation_status: status === "SUCCEEDED" ? "PASS" : "NOT_RUN",
    result_artifact: status === "SUCCEEDED" ? { artifact_id: "RESULT_1", status: "PASS" } : null,
    last_error: status === "RECOVERY_REQUIRED" ? "UNKNOWN_EXTERNAL_OUTCOME" : null,
    recovery_required: status === "RECOVERY_REQUIRED", created_at: "2026-09-15T00:00:00Z",
    started_at: status === "QUEUED" ? null : "2026-09-15T00:00:01Z",
    ended_at: status === "SUCCEEDED" ? "2026-09-15T00:00:02Z" : null,
    updated_at: "2026-09-15T00:00:02Z",
  };
}

const packet = { artifact_id: "ART_" + "a".repeat(32), packet_id: "PACKET_1", run_id: "RUN_1",
  mode: "DEMO" as const, validation_state: "PASS", source: { source_id: "SRC_SYNTHETIC",
    source_sha256: "b".repeat(64), size_bytes: 12, source_type: "SYNTHETIC_TEXT" }, summary: {} };

describe("Durable Jobs operator surface", () => {
  beforeEach(() => {
    vi.clearAllMocks(); window.history.replaceState(null, "", "/jobs");
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "DEMO", csrf_token: "csrf" });
    vi.mocked(loginWorkbench).mockResolvedValue({});
    vi.mocked(listPackets).mockResolvedValue({ packets: [packet] });
    vi.mocked(listCloudJobs).mockResolvedValue({ items: [], total: 0, next_cursor: null, previous_cursor: null });
    vi.mocked(getCloudJobEvents).mockResolvedValue({ items: [] });
    vi.mocked(getCloudJobArtifacts).mockResolvedValue({ items: [], raw_output_exposed: false });
  });

  it("loads a durable terminal job with identities, usage, events, and result metadata", async () => {
    window.history.replaceState(null, "", "/jobs?job=JOB_EXACT");
    const exact = job();
    vi.mocked(listCloudJobs).mockResolvedValue({ items: [exact], total: 1, next_cursor: null, previous_cursor: null });
    vi.mocked(getCloudJob).mockResolvedValue(exact);
    vi.mocked(getCloudJobEvents).mockResolvedValue({ items: [{ sequence: 1, event_type: "JOB_CREATED", event: {}, event_sha256: "c".repeat(64), created_at: "now" }] });
    vi.mocked(getCloudJobArtifacts).mockResolvedValue({ items: [{ result_artifact_id: "RESULT_1", sha256: "d".repeat(64), validation_status: "PASS", created_at: "now" }], raw_output_exposed: false });
    render(<CloudJobsWorkbench />);
    await waitFor(() => expect(listCloudJobs).toHaveBeenCalled());
    expect(await screen.findByRole("heading", { name: "SEMANTIC_DECOMPOSITION" })).toBeInTheDocument();
    expect(screen.getByText("100 input · 20 output · 120 total")).toBeInTheDocument();
    expect(screen.getByText(/DETERMINISTIC_FAKE \/ fake-semantic-v1/)).toBeInTheDocument();
    expect(screen.getByText("JOB_CREATED")).toBeInTheDocument();
    expect(screen.getAllByText("RESULT_1").length).toBeGreaterThan(0);
  });

  it("submits only a registered operation and retries with the same idempotency identity", async () => {
    const queued = job("QUEUED", "JOB_QUEUE");
    vi.mocked(submitCloudJob).mockResolvedValueOnce({ job: queued, duplicate: false })
      .mockResolvedValueOnce({ job: queued, duplicate: true });
    vi.mocked(getCloudJob).mockResolvedValue(queued);
    render(<CloudJobsWorkbench />);
    await screen.findByRole("option", { name: /SRC_SYNTHETIC/ });
    fireEvent.click(screen.getByRole("button", { name: "Queue durable job" }));
    expect(await screen.findByText("Durable job queued for the separate worker.")).toBeInTheDocument();
    const firstBody = vi.mocked(submitCloudJob).mock.calls[0][0];
    expect(firstBody).toMatchObject({ input_artifact_id: packet.artifact_id, operation_kind: "SEMANTIC_DECOMPOSITION" });
    fireEvent.click(screen.getByRole("button", { name: "Retry same submission" }));
    expect(await screen.findByText("Existing durable job returned; no new provider work created.")).toBeInTheDocument();
    expect(vi.mocked(submitCloudJob).mock.calls[1][0]).toEqual(firstBody);
  });

  it("shows unknown usage and blocks automatic action for recovery-required jobs", async () => {
    const recovery = { ...job("RECOVERY_REQUIRED"), usage: { status: "UNKNOWN" as const,
      input_tokens: null, output_tokens: null, total_tokens: null, cached_tokens: null } };
    vi.mocked(listCloudJobs).mockResolvedValue({ items: [recovery], total: 1, next_cursor: null, previous_cursor: null });
    vi.mocked(getCloudJob).mockResolvedValue(recovery);
    window.history.replaceState(null, "", "/jobs?job=JOB_EXACT");
    render(<CloudJobsWorkbench />);
    expect(await screen.findByText("Recovery required. Automatic provider retry is blocked.")).toBeInTheDocument();
    expect(screen.getByText("Usage unknown")).toBeInTheDocument();
    expect(screen.getByText("UNKNOWN_EXTERNAL_OUTCOME")).toBeInTheDocument();
  });

  it("requires the existing Workbench login without provider credentials", async () => {
    vi.mocked(getSession).mockRejectedValue(new WorkbenchError(401));
    render(<CloudJobsWorkbench />);
    expect(await screen.findByRole("heading", { name: "Sign in to inspect job execution" })).toBeInTheDocument();
    expect(screen.getByLabelText("Workbench token")).toHaveAttribute("type", "password");
  });
});
