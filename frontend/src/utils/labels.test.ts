import { describe, expect, it } from "vitest";
import { formatHealTime, humanizeLabel } from "./labels";

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
