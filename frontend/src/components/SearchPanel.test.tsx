import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { searchNodes } from "../api/client";
import { SearchPanel } from "./SearchPanel";

vi.mock("../api/client", () => ({ searchNodes: vi.fn() }));

describe("SearchPanel", () => {
  beforeEach(() => {
    vi.mocked(searchNodes).mockReset();
  });

  it("renders canonical identity and alias match, then selects the Node", async () => {
    const onSelect = vi.fn();
    vi.mocked(searchNodes).mockResolvedValue([
      {
        node_id: "NODE_EML",
        canonical_name: "Electro-Absorption Modulated Laser",
        primary_type: "Product",
        matched_by: "alias",
        matched_text: "EML",
      },
    ]);
    render(<SearchPanel selectedNodeId={null} onSelect={onSelect} />);

    fireEvent.change(screen.getByLabelText("Search nodes or aliases"), {
      target: { value: "  EML  " },
    });

    expect(await screen.findByText("Electro-Absorption Modulated Laser")).toBeInTheDocument();
    expect(screen.getByText("Matched alias: EML")).toBeInTheDocument();
    expect(searchNodes).toHaveBeenCalledWith("EML", 20, expect.any(AbortSignal));

    fireEvent.click(screen.getByRole("button", { name: /Electro-Absorption Modulated Laser/ }));
    expect(onSelect).toHaveBeenCalledWith("NODE_EML");
  });
});
