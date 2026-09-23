import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSession } from "../api/workbench";
import { getResearchCompany } from "../api/research";
import { getOperationalCapacity, getSourceOperation, listSourceOperations, startSourceProcessing } from "../api/sourceOperations";
import { SourceOperationsWorkbench } from "./SourceOperationsWorkbench";

vi.mock("../api/workbench", async () => {
  const actual = await vi.importActual<typeof import("../api/workbench")>("../api/workbench");
  return { ...actual, getSession: vi.fn(), loginWorkbench: vi.fn() };
});
vi.mock("../api/research", () => ({ getResearchCompany: vi.fn(), searchResearchCompanies: vi.fn() }));
vi.mock("../api/sourceOperations", () => ({
  listSourceOperations: vi.fn(), getSourceOperation: vi.fn(), uploadSource: vi.fn(),
  startSourceProcessing: vi.fn(), getOperationalCapacity: vi.fn(),
}));

const source = {
  source_id: "S1", source_sha256: "a".repeat(64), size_bytes: 1024,
  safe_filename: "synthetic.pdf", mime_type: "application/pdf", storage_artifact_id: "ART1",
  validation: { gate: "PASS", pages: 1, ocr_used: false as const },
  known_canonical_source_id: null, uploaded_at: "2026-09-22", private: true as const,
  processing_runs: [], latest_run: null,
};

describe("Source Operations Company Material mode", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState(null, "", "/source-operations/S1?company=C1");
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "PRIVATE", csrf_token: "csrf" });
    vi.mocked(getResearchCompany).mockResolvedValue({ node_id: "C1", canonical_name: "Synthetic Company", primary_type: "Company", status: "active" });
    vi.mocked(listSourceOperations).mockResolvedValue({ items: [source], total: 1, next_cursor: null,
      capabilities: { source_class: "PRIVATE_CLEAN_PDF", mime_types: ["application/pdf"], max_pdf_bytes: 20 * 1024 * 1024,
        single_file: true, ocr_supported: false } });
    vi.mocked(getSourceOperation).mockResolvedValue(source);
    vi.mocked(getOperationalCapacity).mockResolvedValue({ enabled: false, policy_version: null });
    vi.mocked(startSourceProcessing).mockResolvedValue({ run: {} as never, duplicate: false });
  });

  it("validates exact Company context and sends explicitly selected material metadata", async () => {
    render(<SourceOperationsWorkbench />);
    expect(await screen.findByText(/Research target:/)).toHaveTextContent("Synthetic Company");
    expect(screen.getByRole("link", { name: "Back to Company Research" })).toHaveAttribute("href", "/node/C1");
    const start = await screen.findByRole("button", { name: "Start Processing" });
    expect(start).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Material Kind"), { target: { value: "investor_qa" } });
    fireEvent.change(screen.getByLabelText("Source Channel"), { target: { value: "knowledge_community" } });
    fireEvent.change(screen.getByLabelText("Material Date"), { target: { value: "2026-09-22" } });
    fireEvent.change(screen.getByLabelText("Operator Title"), { target: { value: "Synthetic Q&A" } });
    expect(screen.getByText(/Low-trust clue source/)).toBeInTheDocument();
    fireEvent.click(start);
    await waitFor(() => expect(startSourceProcessing).toHaveBeenCalled());
    const body = vi.mocked(startSourceProcessing).mock.calls[0][1] as Record<string, unknown>;
    expect(body.company_material_intent).toEqual({ target_company_node_id: "C1", material_kind: "investor_qa",
      source_channel: "knowledge_community", material_date: "2026-09-22", operator_title: "Synthetic Q&A" });
  });

  it("fails closed when the URL target is not a valid canonical Company", async () => {
    vi.mocked(getResearchCompany).mockRejectedValue(new Error("COMPANY_MATERIAL_TARGET_NOT_COMPANY"));
    render(<SourceOperationsWorkbench />);
    expect(await screen.findByText("COMPANY_MATERIAL_TARGET_NOT_COMPANY")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Start Processing" })).toBeDisabled();
  });
});
