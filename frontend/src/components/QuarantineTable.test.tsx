import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import QuarantineTable from "./QuarantineTable";
import type { QuarantineRow } from "../api/types";

const ROW: QuarantineRow = {
  id: 48,
  run_id: 4,
  original_data: { order_id: "ORD-000050", customer_id: "CUST-9730" },
  error_type: "invalid_foreign_key",
  error_detail: "customer_id: Unknown customer_id: CUST-9730",
  attempt_count: 1,
  diagnosis_history: [
    {
      hypothesis: "customer_id does not exist in the known-customers reference set",
      transform: null,
      confidence: 1.0,
      reasoning: "Unresolvable foreign key has no safe automatic fix.",
      source: "heuristic",
      row_after: null,
    },
  ],
  resolved: false,
  created_at: "2026-07-22T11:04:45.582246",
};

function renderTable(rows: QuarantineRow[] = [ROW]) {
  const onResolve = vi.fn();
  render(<QuarantineTable rows={rows} onResolve={onResolve} />);
  return { onResolve };
}

describe("QuarantineTable keyboard accessibility", () => {
  it("is focusable and exposes button semantics", () => {
    renderTable();
    const row = screen.getByRole("button", { name: /48/ });
    expect(row).toHaveAttribute("tabindex", "0");
    expect(row).toHaveAttribute("aria-expanded", "false");
  });

  it("expands the detail panel on Enter and reflects it in aria-expanded", async () => {
    const user = userEvent.setup();
    renderTable();
    const row = screen.getByRole("button", { name: /48/ });

    row.focus();
    await user.keyboard("{Enter}");

    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(ROW.error_detail)).toBeInTheDocument();
    expect(screen.getByText(/Unresolvable foreign key/)).toBeInTheDocument();
  });

  it("collapses again on a second Enter", async () => {
    const user = userEvent.setup();
    renderTable();
    const row = screen.getByRole("button", { name: /48/ });

    row.focus();
    await user.keyboard("{Enter}");
    expect(row).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Enter}");
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(ROW.error_detail)).not.toBeInTheDocument();
  });

  it("also expands on Space", async () => {
    const user = userEvent.setup();
    renderTable();
    const row = screen.getByRole("button", { name: /48/ });

    row.focus();
    await user.keyboard(" ");

    expect(row).toHaveAttribute("aria-expanded", "true");
  });

  it("does not toggle the row when the nested Resolve button is activated via keyboard", async () => {
    const user = userEvent.setup();
    const { onResolve } = renderTable();
    const row = screen.getByRole("button", { name: /48/ });
    const resolveButton = screen.getByRole("button", { name: "Resolve" });

    resolveButton.focus();
    await user.keyboard("{Enter}");

    expect(onResolve).toHaveBeenCalledWith(48);
    expect(row).toHaveAttribute("aria-expanded", "false");
  });

  it("still expands on a mouse click", async () => {
    const user = userEvent.setup();
    renderTable();
    const row = screen.getByRole("button", { name: /48/ });

    await user.click(row);

    expect(row).toHaveAttribute("aria-expanded", "true");
  });
});
