import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import TriggerRunForm from "./TriggerRunForm";
import { ToastProvider } from "./Toast";
import * as client from "../api/client";
import type { RunSummary } from "../api/types";

vi.mock("../api/client");

const RUN: RunSummary = {
  id: 9,
  started_at: "2026-07-25T11:00:00Z",
  finished_at: "2026-07-25T11:00:01Z",
  row_count: 50,
  clean_first_pass: 40,
  healed: 5,
  quarantined: 5,
  error_types: {},
  fixes_applied: {},
  avg_time_to_heal_ms: null,
  status: "completed",
};

function renderForm(onRunComplete = vi.fn()) {
  render(
    <ToastProvider>
      <TriggerRunForm onRunComplete={onRunComplete} />
    </ToastProvider>
  );
  return { onRunComplete };
}

describe("TriggerRunForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows synthetic-data fields by default", () => {
    renderForm();
    expect(screen.getByLabelText("Row count")).toBeInTheDocument();
    expect(screen.getByLabelText("Failure rate")).toBeInTheDocument();
    expect(screen.getByLabelText("Failure mode")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trigger run" })).toBeInTheDocument();
  });

  it("switches to the upload form and disables submit until a file is chosen", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Upload CSV" }));

    expect(screen.queryByLabelText("Row count")).not.toBeInTheDocument();
    expect(screen.getByLabelText("CSV file")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload & run" })).toBeDisabled();
  });

  it("triggers a synthetic run with the form's values and reports success", async () => {
    vi.mocked(client.triggerRun).mockResolvedValue(RUN);
    const user = userEvent.setup();
    const { onRunComplete } = renderForm();

    await user.clear(screen.getByLabelText("Row count"));
    await user.type(screen.getByLabelText("Row count"), "75");
    await user.selectOptions(screen.getByLabelText("Failure mode"), "encoding_issue");
    await user.click(screen.getByRole("button", { name: "Trigger run" }));

    await waitFor(() =>
      expect(client.triggerRun).toHaveBeenCalledWith({
        row_count: 75,
        failure_rate: 0.2,
        failure_mode: "encoding_issue",
        use_llm: false,
      })
    );
    expect(onRunComplete).toHaveBeenCalledWith(RUN);
    expect(await screen.findByText("Run #9 triggered — 50 rows processed.")).toBeInTheDocument();
  });

  it("shows an inline error banner instead of a toast when triggering fails", async () => {
    vi.mocked(client.triggerRun).mockRejectedValue(new Error("POST /runs/trigger failed: 500"));
    const user = userEvent.setup();
    const { onRunComplete } = renderForm();

    await user.click(screen.getByRole("button", { name: "Trigger run" }));

    expect(await screen.findByText("POST /runs/trigger failed: 500")).toBeInTheDocument();
    expect(onRunComplete).not.toHaveBeenCalled();
    expect(screen.queryByText(/triggered/)).not.toBeInTheDocument();
  });

  it("re-enables the submit button after a failed submission", async () => {
    vi.mocked(client.triggerRun).mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Trigger run" }));

    await screen.findByText("boom");
    expect(screen.getByRole("button", { name: "Trigger run" })).toBeEnabled();
  });
});
