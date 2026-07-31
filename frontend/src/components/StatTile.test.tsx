import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatTile from "./StatTile";

describe("StatTile", () => {
  it("renders the label and value with no info icon when no tooltip is given", () => {
    const { container } = render(<StatTile label="Rows" value="42" />);
    expect(screen.getByText("Rows")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(container.querySelector(".info-icon")).not.toBeInTheDocument();
  });

  it("renders a focusable info icon carrying the tooltip text when given one", () => {
    render(<StatTile label="Auto-heal rate" value="12%" tooltip="Explains the metric." />);
    const icon = screen.getByLabelText("Explains the metric.");
    expect(icon).toHaveAttribute("title", "Explains the metric.");
    expect(icon).toHaveAttribute("tabIndex", "0");
  });
});
