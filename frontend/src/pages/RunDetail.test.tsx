import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RunDetail from "./RunDetail";
import { ToastProvider } from "../components/Toast";
import * as client from "../api/client";
import type { AuditEntry, QuarantineRow, RunSummary } from "../api/types";

vi.mock("../api/client");

const RUN: RunSummary = {
  id: 7,
  started_at: "2026-07-22T11:04:45.582246",
  finished_at: "2026-07-22T11:04:46.102938",
  row_count: 4,
  clean_first_pass: 1,
  healed: 1,
  quarantined: 2,
  error_types: { invalid_amount: 1, invalid_foreign_key: 2 },
  fixes_applied: { coerce_amount: 1 },
  avg_time_to_heal_ms: 0.3,
  status: "completed",
};

// Two of these (ORD-000003, ORD-000004) share the same outcome and transform
// (no_fix / none) so the grouped audit trail should collapse them into a
// single "2 rows" pattern instead of showing them as separate blocks.
const AUDIT: AuditEntry[] = [
  {
    id: 1,
    run_id: 7,
    row_identifier: "ORD-000002",
    hypothesis: "amount has currency noise",
    transform_chosen: "coerce_amount",
    confidence: 0.9,
    reasoning: "stripped a leading dollar sign",
    diagnosis_source: "heuristic",
    outcome: "healed",
    created_at: "2026-07-22T11:04:45.6Z",
  },
  {
    id: 2,
    run_id: 7,
    row_identifier: "ORD-000003",
    hypothesis: "customer_id does not exist",
    transform_chosen: null,
    confidence: 1.0,
    reasoning: "unresolvable foreign key has no safe automatic fix",
    diagnosis_source: "heuristic",
    outcome: "no_fix",
    created_at: "2026-07-22T11:04:45.7Z",
  },
  {
    id: 3,
    run_id: 7,
    row_identifier: "ORD-000004",
    hypothesis: "customer_id does not exist",
    transform_chosen: null,
    confidence: 1.0,
    reasoning: "unresolvable foreign key has no safe automatic fix",
    diagnosis_source: "heuristic",
    outcome: "no_fix",
    created_at: "2026-07-22T11:04:45.8Z",
  },
];

const QUARANTINE_ROW: QuarantineRow = {
  id: 48,
  run_id: 7,
  original_data: { order_id: "ORD-000003", customer_id: "CUST-9730" },
  error_type: "invalid_foreign_key",
  error_detail: "customer_id: Unknown customer_id: CUST-9730",
  attempt_count: 1,
  diagnosis_history: [],
  resolved: false,
  created_at: "2026-07-22T11:04:45.7Z",
};

function renderPage(runId = "7") {
  return render(
    <MemoryRouter initialEntries={[`/runs/${runId}`]}>
      <ToastProvider>
        <Routes>
          <Route path="/runs/:id" element={<RunDetail />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );
}

describe("RunDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(client.getRun).mockResolvedValue(RUN);
    vi.mocked(client.getRunAudit).mockResolvedValue(AUDIT);
    vi.mocked(client.listQuarantine).mockResolvedValue({ items: [QUARANTINE_ROW], total: 1 });
    vi.mocked(client.resolveQuarantineRow).mockResolvedValue({ ...QUARANTINE_ROW, resolved: true });
  });

  it("groups the audit trail by outcome/transform instead of listing every row", async () => {
    const { container } = renderPage();

    expect(await screen.findByText("Run #7")).toBeInTheDocument();

    const headers = Array.from(container.querySelectorAll(".audit-group-header")).map((el) => el.textContent);
    expect(headers).toEqual(["No fix 2 rows · heuristic", "Healed Coerce amount 1 row · heuristic"]);

    // The sample hypothesis/reasoning for each group is visible up front...
    expect(screen.getByText("stripped a leading dollar sign")).toBeInTheDocument();
    expect(screen.getByText("unresolvable foreign key has no safe automatic fix")).toBeInTheDocument();

    // ...but individual row identifiers stay hidden until a group is expanded.
    expect(screen.queryByText("ORD-000002")).not.toBeInTheDocument();
    expect(screen.queryByText("ORD-000003")).not.toBeInTheDocument();
    expect(screen.queryByText("ORD-000004")).not.toBeInTheDocument();
  });

  it("expands a group to reveal its individual rows without expanding the others", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();
    await screen.findByText("Run #7");

    const headers = container.querySelectorAll(".audit-group-header");
    const noFixHeader = Array.from(headers).find((el) => el.textContent?.includes("No fix"));
    expect(noFixHeader).toBeTruthy();

    await user.click(noFixHeader as Element);

    expect(screen.getByText("ORD-000003")).toBeInTheDocument();
    expect(screen.getByText("ORD-000004")).toBeInTheDocument();
    // The healed group was never clicked, so it stays collapsed.
    expect(screen.queryByText("ORD-000002")).not.toBeInTheDocument();
  });

  it("lists quarantined rows from this run and can resolve them", async () => {
    renderPage();
    await screen.findByText("Run #7");

    const resolveButton = await screen.findByRole("button", { name: "Resolve" });
    await userEvent.click(resolveButton);

    await waitFor(() => expect(client.resolveQuarantineRow).toHaveBeenCalledWith(48));
    expect(client.listQuarantine).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Row #48 resolved.")).toBeInTheDocument();
  });

  it("shows an error toast instead of failing silently when resolving fails", async () => {
    vi.mocked(client.resolveQuarantineRow).mockRejectedValue(
      new Error("POST /quarantine/48/resolve failed: 500")
    );
    renderPage();
    await screen.findByText("Run #7");

    const resolveButton = await screen.findByRole("button", { name: "Resolve" });
    await userEvent.click(resolveButton);

    expect(await screen.findByText("POST /quarantine/48/resolve failed: 500")).toBeInTheDocument();
    expect(client.listQuarantine).toHaveBeenCalledTimes(1);
  });

  it("notes when the quarantine list is truncated", async () => {
    vi.mocked(client.listQuarantine).mockResolvedValue({ items: [QUARANTINE_ROW], total: 823 });
    renderPage();

    expect(await screen.findByText("Showing 1 of 823 quarantined rows.")).toBeInTheDocument();
  });

  it("shows a not-found state when the run doesn't exist", async () => {
    vi.mocked(client.getRun).mockRejectedValue(new Error("GET /runs/999 failed: 404"));
    renderPage("999");

    expect(await screen.findByText("Run #999 not found.")).toBeInTheDocument();
  });
});
