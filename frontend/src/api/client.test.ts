import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  getCurrentView,
  getCurrentViewHistory,
  getHealth,
  getKnowledgeGaps,
  getNode,
  getResearchQuestion,
  getSourceDetail,
  searchNodes,
} from "./client";

describe("API client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("returns a successful JSON response", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
    });

    await expect(getHealth()).resolves.toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("throws a typed error for non-2xx responses", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Node not found" }),
    });

    await expect(getNode("NODE_MISSING")).rejects.toEqual(
      new ApiError("Node not found", 404),
    );
  });

  it("encodes deterministic search query parameters", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => [] });

    await searchNodes("EML & optical", 20);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/nodes/search?q=EML+%26+optical&limit=20",
    );
  });

  it("uses the typed knowledge detail endpoints", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => null });

    await getCurrentView("NODE / 1");
    await getCurrentViewHistory("NODE / 1");
    await getResearchQuestion("NODE / 1");
    await getKnowledgeGaps("NODE / 1");
    await getSourceDetail("SRC / 1");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/nodes/NODE%20%2F%201/current-view",
      "/api/nodes/NODE%20%2F%201/current-view-history",
      "/api/nodes/NODE%20%2F%201/research-question",
      "/api/nodes/NODE%20%2F%201/knowledge-gaps",
      "/api/sources/SRC%20%2F%201",
    ]);
  });
});
