import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Quarantine from "./Quarantine";
import { ToastProvider } from "../components/Toast";
import * as client from "../api/client";
import type { QuarantineRow } from "../api/types";

vi.mock("../api/client");

const ROW: QuarantineRow = {
  id: 48,
  run_id: 4,
  original_data: { order_id: "ORD-000050", customer_id: "CUST-9730" },
  error_type: "invalid_foreign_key",
  error_detail: "customer_id: Unknown customer_id: CUST-9730",
  attempt_count: 1,
  diagnosis_history: [],
  resolved: false,
  created_at: "2026-07-22T11:04:45.582246",
};

function renderPage() {
  return render(
    <ToastProvider>
      <Quarantine />
    </ToastProvider>
  );
}

describe("Quarantine resolve feedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(client.listQuarantine).mockResolvedValue({ items: [ROW], total: 1 });
  });

  it("shows a success toast when resolving succeeds", async () => {
    vi.mocked(client.resolveQuarantineRow).mockResolvedValue({ ...ROW, resolved: true });
    const user = userEvent.setup();
    renderPage();

    const resolveButton = await screen.findByRole("button", { name: "Resolve" });
    await user.click(resolveButton);

    expect(await screen.findByText("Row #48 resolved.")).toBeInTheDocument();
  });

  it("shows an error toast instead of failing silently when resolving fails", async () => {
    vi.mocked(client.resolveQuarantineRow).mockRejectedValue(new Error("POST /quarantine/48/resolve failed: 500"));
    const user = userEvent.setup();
    renderPage();

    const resolveButton = await screen.findByRole("button", { name: "Resolve" });
    await user.click(resolveButton);

    expect(await screen.findByText("POST /quarantine/48/resolve failed: 500")).toBeInTheDocument();
    await waitFor(() => expect(client.listQuarantine).toHaveBeenCalledTimes(1));
  });
});
