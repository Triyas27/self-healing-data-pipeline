import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import RunsTable from "./RunsTable";
import type { RunSummary } from "../api/types";

const RUN: RunSummary = {
  id: 12,
  started_at: "2026-07-22T11:04:45.582246",
  finished_at: "2026-07-22T11:04:46.102938",
  row_count: 50,
  clean_first_pass: 40,
  healed: 7,
  quarantined: 3,
  error_types: { invalid_amount: 2, invalid_foreign_key: 1 },
  fixes_applied: { coerce_amount: 2 },
  avg_time_to_heal_ms: 0.42,
  status: "completed",
};

function renderTable(runs: RunSummary[] = [RUN]) {
  render(<RunsTable runs={runs} />);
}

describe("RunsTable error/fix breakdown", () => {
  it("hides the breakdown until the row is expanded", () => {
    renderTable();
    expect(screen.queryByText("Invalid amount")).not.toBeInTheDocument();
  });

  it("shows humanized error type and fix chips on expand", async () => {
    const user = userEvent.setup();
    renderTable();
    const row = screen.getByRole("button", { name: /12/ });

    await user.click(row);

    expect(screen.getByText("Invalid amount")).toBeInTheDocument();
    expect(screen.getByText("Invalid foreign key")).toHaveTextContent("Invalid foreign key ×1");
    expect(screen.getByText("Coerce amount")).toHaveTextContent("Coerce amount ×2");
    expect(screen.getByText(/0\.42 ms\/row/)).toBeInTheDocument();
  });

  it("shows fallback copy when a run has no errors or fixes", async () => {
    const user = userEvent.setup();
    renderTable([{ ...RUN, error_types: {}, fixes_applied: {} }]);
    const row = screen.getByRole("button", { name: /12/ });

    await user.click(row);

    expect(screen.getByText("No validation errors on this run.")).toBeInTheDocument();
    expect(screen.getByText("No automated fixes were needed.")).toBeInTheDocument();
  });
});
