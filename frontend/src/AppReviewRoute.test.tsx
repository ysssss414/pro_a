import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api/client", async (original) => ({ ...await original<typeof import("./api/client")>(),
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }), getStats: vi.fn().mockResolvedValue(null),
}));
vi.mock("./api/workbench", async (original) => ({ ...await original<typeof import("./api/workbench")>(),
  getSession: vi.fn().mockResolvedValue({ actor: "operator", mode: "DEMO" }),
  listPackets: vi.fn().mockResolvedValue({ packets: [] }),
}));

it("opens Review directly from the route while retaining Explorer navigation", async () => {
  window.history.replaceState(null, "", "/?surface=review");
  try {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Native Review" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Review" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Explorer" })).toBeVisible();
    expect(await screen.findByText(/No registered packets/)).toBeVisible();
  } finally {
    window.history.replaceState(null, "", "/");
  }
});
