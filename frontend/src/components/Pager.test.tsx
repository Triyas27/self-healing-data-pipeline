import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Pager from "./Pager";

describe("Pager", () => {
  it("renders nothing when there's nothing to page through", () => {
    const { container } = render(<Pager total={0} limit={10} offset={0} onOffsetChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("disables Previous on the first page and enables Next", () => {
    render(<Pager total={25} limit={10} offset={0} onOffsetChange={vi.fn()} />);

    expect(screen.getByText("1–10 of 25")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  it("enables both buttons on a middle page", () => {
    render(<Pager total={25} limit={10} offset={10} onOffsetChange={vi.fn()} />);

    expect(screen.getByText("11–20 of 25")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  it("clamps the displayed end to the total on the last, partial page and disables Next", () => {
    render(<Pager total={25} limit={10} offset={20} onOffsetChange={vi.fn()} />);

    expect(screen.getByText("21–25 of 25")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled();
  });

  it("steps forward by limit when Next is clicked", async () => {
    const onOffsetChange = vi.fn();
    const user = userEvent.setup();
    render(<Pager total={25} limit={10} offset={0} onOffsetChange={onOffsetChange} />);

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onOffsetChange).toHaveBeenCalledWith(10);
  });

  it("steps back by limit when Previous is clicked", async () => {
    const onOffsetChange = vi.fn();
    const user = userEvent.setup();
    render(<Pager total={25} limit={10} offset={20} onOffsetChange={onOffsetChange} />);

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(onOffsetChange).toHaveBeenCalledWith(10);
  });

  it("clamps Previous at 0 rather than going negative", async () => {
    const onOffsetChange = vi.fn();
    const user = userEvent.setup();
    // offset=5 with limit=10 is an unusual but possible state (e.g. after a resize of page size);
    // Previous should still clamp to 0, not -5.
    render(<Pager total={25} limit={10} offset={5} onOffsetChange={onOffsetChange} />);

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(onOffsetChange).toHaveBeenCalledWith(0);
  });
});
