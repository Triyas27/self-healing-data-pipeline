import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HealRateTooltipContent } from "./HealRateChart";

describe("HealRateTooltipContent", () => {
  it("shows row count alongside heal rate so runs of different sizes aren't visually identical", () => {
    render(
      <HealRateTooltipContent
        active
        payload={[{ payload: { run: "#5", healRate: 63.7, rowCount: 300 } }]}
      />
    );

    expect(screen.getByText("#5")).toBeInTheDocument();
    expect(screen.getByText("63.7% heal rate")).toBeInTheDocument();
    expect(screen.getByText("300 rows")).toBeInTheDocument();
  });

  it("renders nothing when inactive", () => {
    const { container } = render(
      <HealRateTooltipContent active={false} payload={[{ payload: { run: "#5", healRate: 63.7, rowCount: 300 } }]} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there's no payload", () => {
    const { container } = render(<HealRateTooltipContent active payload={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
