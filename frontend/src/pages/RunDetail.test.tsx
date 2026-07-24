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
  row_count: 3,
  clean_first_pass: 1,
  healed: 1,
  quarantined: 1,
  error_types: { invalid_amount: 1, invalid_foreign_key: 1 },
  fixes_applied: { coerce_amount: 1 },
  avg_time_to_heal_ms: 0.3,
  status: "completed",
};

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

  it("shows the run summary and per-row audit trail", async () => {
    const { container } = renderPage();

    expect(await screen.findByText("Run #7")).toBeInTheDocument();
    expect(screen.getByText("ORD-000002")).toBeInTheDocument();
    expect(screen.getByText("ORD-000003")).toBeInTheDocument();
    const badgeText = Array.from(container.querySelectorAll(".attempt .badge")).map((el) => el.textContent);
    expect(badgeText).toEqual(["Healed", "No fix"]);
    expect(screen.getByText("stripped a leading dollar sign")).toBeInTheDocument();
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
