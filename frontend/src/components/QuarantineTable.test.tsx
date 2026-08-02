import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
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
  render(
    <MemoryRouter>
      <QuarantineTable rows={rows} onResolve={onResolve} />
    </MemoryRouter>
  );
  return { onResolve };
}

describe("QuarantineTable", () => {
  it("humanizes the error type and explains what Resolve does", () => {
    renderTable();

    expect(screen.getByText("Invalid foreign key")).toBeInTheDocument();
    expect(screen.queryByText("invalid_foreign_key")).not.toBeInTheDocument();

    const resolveButton = screen.getByRole("button", { name: "Resolve" });
    expect(resolveButton).toHaveAttribute(
      "title",
      "Marks this row as reviewed by a human. Doesn't change the data or re-run the pipeline."
    );
  });

  it("links the run column to that run's detail page without expanding the row", async () => {
    const user = userEvent.setup();
    renderTable();

    const runLink = screen.getByRole("link", { name: "#4" });
    expect(runLink).toHaveAttribute("href", "/runs/4");

    await user.click(runLink);
    expect(screen.getByRole("button", { name: /48/ })).toHaveAttribute("aria-expanded", "false");
  });

  it("humanizes the transform in the expanded attempt history, or shows 'No fix'", async () => {
    const user = userEvent.setup();
    renderTable();
    const row = screen.getByRole("button", { name: /48/ });

    await user.click(row);

    expect(screen.getByText("No fix")).toBeInTheDocument();
  });
});

describe("QuarantineTable grouped by error type", () => {
  const ROW_A1: QuarantineRow = { ...ROW, id: 10, run_id: 1, error_type: "invalid_amount", resolved: false };
  const ROW_A2: QuarantineRow = { ...ROW, id: 11, run_id: 2, error_type: "invalid_amount", resolved: false };
  const ROW_B1: QuarantineRow = { ...ROW, id: 12, run_id: 3, error_type: "duplicate_order_id", resolved: true };
  const GROUPED_ROWS = [ROW_A1, ROW_A2, ROW_B1];

  function renderGrouped(rows: QuarantineRow[] = GROUPED_ROWS) {
    const onResolve = vi.fn();
    render(
      <MemoryRouter>
        <QuarantineTable rows={rows} onResolve={onResolve} groupByErrorType />
      </MemoryRouter>
    );
    return { onResolve };
  }

  it("collapses same-error-type rows into one header instead of listing every row", () => {
    renderGrouped();

    expect(screen.getByRole("button", { name: /Invalid amount.*2 rows.*2 unresolved/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Duplicate order ID.*1 row\b/ })).toBeInTheDocument();
    // A fully-resolved group shouldn't claim any rows are unresolved.
    expect(screen.queryByText(/Duplicate order ID.*unresolved/)).not.toBeInTheDocument();

    expect(screen.queryByText("#10")).not.toBeInTheDocument();
    expect(screen.queryByText("#11")).not.toBeInTheDocument();
    expect(screen.queryByText("#12")).not.toBeInTheDocument();
  });

  it("expands one group to reveal its rows without expanding the others", async () => {
    const user = userEvent.setup();
    renderGrouped();

    await user.click(screen.getByRole("button", { name: /Invalid amount/ }));

    expect(screen.getByText("#10")).toBeInTheDocument();
    expect(screen.getByText("#11")).toBeInTheDocument();
    expect(screen.queryByText("#12")).not.toBeInTheDocument();
  });
});

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
