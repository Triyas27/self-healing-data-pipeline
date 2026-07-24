import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ToastProvider, useToast } from "./Toast";

function TestButtons() {
  const { showSuccess, showError } = useToast();
  return (
    <div>
      <button onClick={() => showSuccess("It worked.")}>fire success</button>
      <button onClick={() => showError("It broke.")}>fire error</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <ToastProvider>
      <TestButtons />
    </ToastProvider>
  );
}

describe("Toast", () => {
  it("shows a success toast styled distinctly from an error toast", async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByText("fire success"));
    const toast = await screen.findByText("It worked.");
    expect(toast).toHaveClass("toast-success");

    await user.click(screen.getByText("fire error"));
    const errorToast = await screen.findByText("It broke.");
    expect(errorToast).toHaveClass("toast-error");
  });

  it("dismisses a toast when clicked", async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByText("fire success"));
    const toast = await screen.findByText("It worked.");

    await user.click(toast);
    expect(screen.queryByText("It worked.")).not.toBeInTheDocument();
  });

  it("auto-dismisses after a timeout", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderWithProvider();

    await user.click(screen.getByText("fire success"));
    expect(await screen.findByText("It worked.")).toBeInTheDocument();

    vi.advanceTimersByTime(5000);
    await waitFor(() => expect(screen.queryByText("It worked.")).not.toBeInTheDocument());

    vi.useRealTimers();
  });

  it("throws when used outside a provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    function Bare() {
      useToast();
      return null;
    }
    expect(() => render(<Bare />)).toThrow("useToast must be used within a ToastProvider");
    spy.mockRestore();
  });
});
