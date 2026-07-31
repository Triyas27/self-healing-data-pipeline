import { describe, expect, it } from "vitest";
import { formatHealTime, humanizeLabel, summarizeRun } from "./labels";
import type { RunSummary } from "../api/types";

const BASE_RUN: RunSummary = {
  id: 1,
  started_at: "2026-07-22T11:04:45.582246",
  finished_at: "2026-07-22T11:04:46.102938",
  row_count: 60,
  clean_first_pass: 27,
  healed: 10,
  quarantined: 23,
  error_types: { invalid_order_date: 10, invalid_amount: 5 },
  fixes_applied: { reformat_date: 10 },
  avg_time_to_heal_ms: 0.4,
  status: "completed",
};

describe("humanizeLabel", () => {
  it("turns snake_case into a capitalized phrase", () => {
    expect(humanizeLabel("invalid_amount")).toBe("Invalid amount");
    expect(humanizeLabel("fix_encoding")).toBe("Fix encoding");
  });

  it("uppercases a trailing id segment", () => {
    expect(humanizeLabel("duplicate_order_id")).toBe("Duplicate order ID");
    expect(humanizeLabel("invalid_customer_id")).toBe("Invalid customer ID");
  });

  it("passes through a single word", () => {
    expect(humanizeLabel("healed")).toBe("Healed");
  });
});

describe("formatHealTime", () => {
  it("shows extra precision for sub-millisecond heals instead of rounding to 0.0", () => {
    expect(formatHealTime(0.03)).toBe("0.03 ms/row");
    expect(formatHealTime(0.4)).toBe("0.40 ms/row");
  });

  it("shows one decimal for single-digit millisecond values", () => {
    expect(formatHealTime(4.2)).toBe("4.2 ms/row");
  });

  it("rounds larger values to whole milliseconds", () => {
    expect(formatHealTime(842.7)).toBe("843 ms/row");
  });

  it("handles exactly zero", () => {
    expect(formatHealTime(0)).toBe("0 ms/row");
  });
});

describe("summarizeRun", () => {
  it("describes a mixed run: what went wrong, what got fixed, what got quarantined", () => {
    expect(summarizeRun(BASE_RUN)).toBe(
      "33 rows had errors (mostly invalid order date), 10 auto-fixed (mainly reformat date), 23 quarantined."
    );
  });

  it("says nothing needed fixing when every row was clean", () => {
    const run = { ...BASE_RUN, clean_first_pass: 60, healed: 0, quarantined: 0, error_types: {}, fixes_applied: {} };
    expect(summarizeRun(run)).toBe("All 60 rows clean, no repairs needed.");
  });

  it("omits the auto-fixed clause when nothing was healed", () => {
    const run = { ...BASE_RUN, healed: 0, quarantined: 33, fixes_applied: {} };
    expect(summarizeRun(run)).toBe("33 rows had errors (mostly invalid order date), 33 quarantined.");
  });

  it("omits the quarantined clause when everything was healed", () => {
    const run = { ...BASE_RUN, healed: 33, quarantined: 0, fixes_applied: { reformat_date: 33 } };
    expect(summarizeRun(run)).toBe(
      "33 rows had errors (mostly invalid order date), 33 auto-fixed (mainly reformat date)."
    );
  });

  it("uses a singular row when only one error row exists", () => {
    const run = { ...BASE_RUN, healed: 0, quarantined: 1, error_types: { invalid_amount: 1 }, fixes_applied: {} };
    expect(summarizeRun(run)).toBe("1 row had errors (mostly invalid amount), 1 quarantined.");
  });

  it("describes a schema-drift rejection distinctly from a normal completed run", () => {
    expect(summarizeRun({ ...BASE_RUN, status: "rejected_schema_drift" })).toBe(
      "Batch rejected: unexpected column(s) in the CSV (schema drift)."
    );
  });

  it("describes a failed run distinctly", () => {
    expect(summarizeRun({ ...BASE_RUN, status: "failed" })).toBe("Run failed unexpectedly partway through.");
  });

  it("describes a still-running run distinctly", () => {
    expect(summarizeRun({ ...BASE_RUN, status: "running" })).toBe("Still running...");
  });
});
