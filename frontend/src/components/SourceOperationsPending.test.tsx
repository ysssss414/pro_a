import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSession } from "../api/workbench";
import { getResearchCompany } from "../api/research";
import { getCommunityDomains, getOperationalCapacity, getSourceOperation, importCommunity,
  listSourceOperations, previewCommunity } from "../api/sourceOperations";
import { SourceOperationsWorkbench } from "./SourceOperationsWorkbench";

vi.mock("../api/workbench", async () => {
  const actual = await vi.importActual<typeof import("../api/workbench")>("../api/workbench");
  return { ...actual, getSession: vi.fn() };
});
vi.mock("../api/research", () => ({ getResearchCompany: vi.fn(), searchResearchCompanies: vi.fn() }));
vi.mock("../api/sourceOperations", () => ({
  listSourceOperations: vi.fn(), getSourceOperation: vi.fn(), uploadSource: vi.fn(),
  startSourceProcessing: vi.fn(), getOperationalCapacity: vi.fn(), getCommunityDomains: vi.fn(),
  previewCommunity: vi.fn(), importCommunity: vi.fn(),
}));

const source = {
  source_id: "S1", source_sha256: "a".repeat(64), size_bytes: 1024,
  safe_filename: "synthetic.pdf", mime_type: "application/pdf", storage_artifact_id: "ART1",
  validation: { gate: "PASS", pages: 1, ocr_used: false as const },
  known_canonical_source_id: null, uploaded_at: "2026-09-23", private: true as const,
  processing_runs: [], latest_run: null,
};
const preview = {
  target_company: { node_id: "C1", canonical_name: "Synthetic Company" },
  company_input: "Synthetic Company", group_id: "group1", group_label: "Synthetic Group",
  topic_count: 1, date_min: null, date_max: null, bundle_id: "B1",
  bundle_sha256: "b".repeat(64), trust_policy: "LOW_TRUST_CLUE_ONLY",
  processing_scope: { mode: "SHARED_CORE_PENDING" as const, domain_assignment_status: "PENDING" as const },
};

describe("Shared Core pending intake", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState(null, "", "/source-operations?company=C1&community=1");
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "PRIVATE", csrf_token: "csrf" });
    vi.mocked(getResearchCompany).mockResolvedValue({ node_id: "C1", canonical_name: "Synthetic Company", primary_type: "Company", status: "active" });
    vi.mocked(getCommunityDomains).mockResolvedValue({ items: [] });
    vi.mocked(listSourceOperations).mockResolvedValue({ items: [], total: 0, next_cursor: null,
      capabilities: { source_class: "PRIVATE_CLEAN_PDF", mime_types: ["application/pdf"],
        max_pdf_bytes: 20 * 1024 * 1024, single_file: true, ocr_supported: false } });
    vi.mocked(getOperationalCapacity).mockResolvedValue({ enabled: false, policy_version: null });
    vi.mocked(getSourceOperation).mockResolvedValue(source);
    vi.mocked(previewCommunity).mockResolvedValue(preview);
    vi.mocked(importCommunity).mockResolvedValue({ preview, source, run: {} as never, duplicate: false });
  });

  it("imports with zero registered Domains and omits the Domain header value", async () => {
    render(<SourceOperationsWorkbench />);
    await screen.findByText(/Research target:/);
    fireEvent.change(screen.getByLabelText("ZSXQ export ZIP"), {
      target: { files: [new File(["synthetic"], "synthetic.zip", { type: "application/zip" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview bundle" }));
    expect(await screen.findByText("Shared Core — Domain pending")).toBeInTheDocument();
    const submit = screen.getByRole("button", { name: "Import and start processing" });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    await waitFor(() => expect(importCommunity).toHaveBeenCalled());
    expect(vi.mocked(importCommunity).mock.calls[0][2]).toBeNull();
  });

  it("keeps a registered Domain as an explicit optional choice", async () => {
    vi.mocked(getCommunityDomains).mockResolvedValue({ items: [{ domain_id: "ai_hardware", version: "1.0.0", sha256: "c".repeat(64) }] });
    render(<SourceOperationsWorkbench />);
    await screen.findByText(/Research target:/);
    fireEvent.change(screen.getByLabelText("ZSXQ export ZIP"), {
      target: { files: [new File(["synthetic"], "synthetic.zip", { type: "application/zip" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview bundle" }));
    await screen.findByText("Shared Core — Domain pending");
    fireEvent.change(screen.getByLabelText("Processing scope"), { target: { value: "ai_hardware" } });
    fireEvent.click(screen.getByRole("button", { name: "Import and start processing" }));
    await waitFor(() => expect(importCommunity).toHaveBeenCalled());
    expect(vi.mocked(importCommunity).mock.calls[0][2]).toBe("ai_hardware");
  });
});
