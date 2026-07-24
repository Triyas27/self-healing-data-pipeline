import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./pages/Dashboard", () => ({
  default: () => {
    throw new Error("boom");
  },
}));
vi.mock("./pages/Quarantine", () => ({ default: () => <div>quarantine page content</div> }));
vi.mock("./pages/RunDetail", () => ({ default: () => null }));

describe("App error containment", () => {
  it("keeps the nav usable when a page crashes instead of blanking the whole app", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Quarantine" })).toBeInTheDocument();
    expect(screen.getByText("Something went wrong loading this page.")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("recovers when navigating away from a crashed page instead of staying stuck", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText("Something went wrong loading this page.")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Quarantine" }));

    expect(screen.getByText("quarantine page content")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong loading this page.")).not.toBeInTheDocument();
    spy.mockRestore();
  });
});
