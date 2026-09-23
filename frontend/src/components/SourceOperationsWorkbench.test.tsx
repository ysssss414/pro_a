import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSession } from "../api/workbench";
import { getOperationalCapacity, getSourceOperation, listSourceOperations } from "../api/sourceOperations";
import { SourceOperationsWorkbench } from "./SourceOperationsWorkbench";

vi.mock("../api/workbench", async () => {
  const actual = await vi.importActual<typeof import("../api/workbench")>("../api/workbench");
  return { ...actual, getSession: vi.fn(), loginWorkbench: vi.fn() };
});
vi.mock("../api/sourceOperations", () => ({
  listSourceOperations: vi.fn(), getSourceOperation: vi.fn(), uploadSource: vi.fn(),
  startSourceProcessing: vi.fn(), getOperationalCapacity: vi.fn(),
}));

const source = {
  source_id: "SRC_STAGE7", source_sha256: "a".repeat(64), size_bytes: 1024,
  safe_filename: "synthetic-private.pdf", mime_type: "application/pdf",
  storage_artifact_id: "SOURCE_BYTES_STAGE7", validation: { gate: "PASS", pages: 1, ocr_used: false as const },
  known_canonical_source_id: null, uploaded_at: "2026-09-15T00:00:00Z", private: true as const,
  processing_runs: [], latest_run: null,
};

describe("Source Operations product surface", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/source-operations");
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "PRIVATE", csrf_token: "csrf" });
    vi.mocked(listSourceOperations).mockResolvedValue({ items: [source], total: 1, next_cursor: null,
      capabilities: { source_class: "PRIVATE_CLEAN_PDF", mime_types: ["application/pdf"], max_pdf_bytes: 20 * 1024 * 1024,
        single_file: true, ocr_supported: false } });
    vi.mocked(getSourceOperation).mockResolvedValue(source);
    vi.mocked(getOperationalCapacity).mockResolvedValue({
      enabled: true, policy_version: "phase43-stage1-bounded-operator-v1",
      capacity_policy_version: "phase43-stage6-lifecycle-capacity-v1",
      operational_pending_rows: 0, native_pending_rows: 0,
      historical_lifecycle_closed: 274, human_user_qualified: 105,
      ai_policy_closed: 169, followup_governance: 40,
      wip_state: "OPEN", new_intake_allowed: true,
      pending_semantics: "OPERATIONAL_PENDING",
    });
  });

  it("presents the bounded private clean-PDF upload and separate processing action", async () => {
    render(<SourceOperationsWorkbench />);
    expect(await screen.findByRole("heading", { name: "Source Operations" })).toBeInTheDocument();
    expect(screen.getByLabelText("Private PDF")).toHaveAttribute("accept", "application/pdf,.pdf");
    expect(await screen.findByText("synthetic-private.pdf")).toBeInTheDocument();
    expect(screen.getByDisplayValue("20 MiB maximum · OCR unsupported")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Operational WIP capacity" })).toHaveTextContent(
      "274 historical lifecycle closures"
    );
  });

  it.each([
    ["SOFT_WARNING", 101, true],
    ["HARD_STOP", 201, false],
  ] as const)("renders %s from operational WIP", async (state, pending, allowed) => {
    vi.mocked(getOperationalCapacity).mockResolvedValue({
      enabled: true, policy_version: "phase43-stage1-bounded-operator-v1",
      capacity_policy_version: "phase43-stage6-lifecycle-capacity-v1",
      operational_pending_rows: pending, native_pending_rows: 274,
      historical_lifecycle_closed: 274, human_user_qualified: 105,
      ai_policy_closed: 169, followup_governance: 40,
      wip_state: state, new_intake_allowed: allowed,
      pending_semantics: "OPERATIONAL_PENDING",
    });
    render(<SourceOperationsWorkbench />);
    const banner = await screen.findByRole("region", { name: "Operational WIP capacity" });
    expect(banner).toHaveTextContent(`Operational WIP · ${state}`);
    expect(banner).toHaveTextContent(`${pending} operational pending · 274 native pending`);
    expect(banner).toHaveTextContent(`new intake ${allowed ? "allowed" : "blocked"}`);
  });

  it("shows manual recovery and never offers a browser Apply action", async () => {
    const recovery = { ...source, latest_run: {
      processing_run_id: "SOURCE_RUN_STAGE7", source_id: source.source_id,
      source_sha256: source.source_sha256, state: "RECOVERY_REQUIRED", stage: "SEMANTIC_JOB",
      runtime_identity: { runtime_sha256: "b".repeat(64) }, native_execution_id: "EXEC_STAGE7",
      native_checkpoint: { available: true, completed_stage: "SEMANTIC_JOB" }, packet_artifact_id: null,
      packet_id: null, error: { code: "UNKNOWN_EXTERNAL_OUTCOME", stage: "SEMANTIC_JOB",
        retry_safe: false, manual_recovery_required: true, operator_action: "Manual job reconciliation is required." },
      jobs: [], usage: { status: "UNKNOWN" as const, input_tokens: null, output_tokens: null, total_tokens: null, attempts: 1 },
      review: null, attribution: null, qualification: null, activation_receipt: null,
      lineage: [{ kind: "SOURCE", id: source.source_id }], created_at: "2026-09-15", updated_at: "2026-09-15", ended_at: "2026-09-15",
    }};
    window.history.replaceState(null, "", "/source-operations/SRC_STAGE7");
    vi.mocked(listSourceOperations).mockResolvedValue({ items: [recovery], total: 1, next_cursor: null,
      capabilities: { source_class: "PRIVATE_CLEAN_PDF", mime_types: ["application/pdf"], max_pdf_bytes: 20 * 1024 * 1024,
        single_file: true, ocr_supported: false } });
    vi.mocked(getSourceOperation).mockResolvedValue(recovery);
    render(<SourceOperationsWorkbench />);
    expect(await screen.findByText("UNKNOWN_EXTERNAL_OUTCOME")).toBeInTheDocument();
    expect(screen.getByText("Manual job reconciliation is required.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply/i })).not.toBeInTheDocument();
  });

  it("uses the canonical Research Source route after activation", async () => {
    const activated = { ...source, latest_run: {
      processing_run_id: "SOURCE_RUN_STAGE7", source_id: source.source_id,
      source_sha256: source.source_sha256, state: "ACTIVATED", stage: "HUMAN_REVIEW",
      runtime_identity: { runtime_sha256: "b".repeat(64) }, native_execution_id: "EXEC_STAGE7",
      native_checkpoint: { available: true, completed_stage: "HUMAN_REVIEW" }, packet_artifact_id: "ART_STAGE7",
      packet_id: "PACKET_STAGE7", error: null, jobs: [],
      usage: { status: "KNOWN" as const, input_tokens: 10, output_tokens: 5, total_tokens: 15, attempts: 2 },
      review: { review_id: "REVIEW_STAGE7", status: "SEALED", required: 2, completed: 2, deep_link: "/?surface=review&artifact=ART_STAGE7" },
      attribution: { status: "SEALED", sidecar_id: "ATTRIBUTION_STAGE7", required: 1, completed: 1 },
      qualification: { object_id: "OPERATIONAL_STAGE7", status: "AWAITING_OPERATOR_ACTION", diff_id: "DIFF_STAGE7" },
      activation_receipt: { object_id: "EXECUTION_STAGE7", status: "EXECUTED" },
      lineage: [{ kind: "SOURCE", id: source.source_id }], created_at: "2026-09-15", updated_at: "2026-09-15", ended_at: "2026-09-15",
    }};
    vi.mocked(listSourceOperations).mockResolvedValue({ items: [activated], total: 1, next_cursor: null,
      capabilities: { source_class: "PRIVATE_CLEAN_PDF", mime_types: ["application/pdf"], max_pdf_bytes: 20 * 1024 * 1024,
        single_file: true, ocr_supported: false } });
    vi.mocked(getSourceOperation).mockResolvedValue(activated);
    window.history.replaceState(null, "", "/source-operations/SRC_STAGE7");
    render(<SourceOperationsWorkbench />);
    expect(await screen.findByRole("link", { name: "Inspect activated Source in Research" }))
      .toHaveAttribute("href", "/source/SRC_STAGE7");
  });

  it("shows pending processing scope in Source detail", async () => {
    const pending = { ...source, latest_run: {
      processing_run_id: "SOURCE_RUN_PENDING", source_id: source.source_id,
      source_sha256: source.source_sha256, state: "HUMAN_REVIEW_REQUIRED", stage: "HUMAN_REVIEW",
      processing_scope_mode: "SHARED_CORE" as const, domain_assignment_status: "PENDING" as const,
      primary_domain: null, runtime_identity: { runtime_sha256: "b".repeat(64) },
      native_execution_id: "EXEC_PENDING", native_checkpoint: { available: true, completed_stage: "HUMAN_REVIEW" },
      packet_artifact_id: "ART_PENDING", packet_id: "PACKET_PENDING", error: null, jobs: [],
      usage: { status: "UNKNOWN" as const, input_tokens: null, output_tokens: null, total_tokens: null, attempts: 0 },
      review: null, attribution: null, qualification: null, activation_receipt: null,
      lineage: [{ kind: "SOURCE", id: source.source_id }], created_at: "2026-09-23", updated_at: "2026-09-23",
    } };
    window.history.replaceState(null, "", "/source-operations/SRC_STAGE7");
    vi.mocked(listSourceOperations).mockResolvedValue({ items: [pending], total: 1, next_cursor: null,
      capabilities: { source_class: "PRIVATE_CLEAN_PDF", mime_types: ["application/pdf"],
        max_pdf_bytes: 20 * 1024 * 1024, single_file: true, ocr_supported: false } });
    vi.mocked(getSourceOperation).mockResolvedValue(pending);
    render(<SourceOperationsWorkbench />);
    expect(await screen.findByText("Industry routing is intentionally deferred until the extracted evidence is reviewed.")).toBeInTheDocument();
    expect(screen.getByText("Shared Core")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
