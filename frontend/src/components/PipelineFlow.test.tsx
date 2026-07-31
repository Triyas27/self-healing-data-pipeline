import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PipelineFlow from "./PipelineFlow";

describe("PipelineFlow", () => {
  it("shows every pipeline stage and both terminal outcomes", () => {
    render(<PipelineFlow />);

    for (const stage of ["Ingest", "Validate", "Diagnose", "Repair"]) {
      expect(screen.getByRole("heading", { name: stage })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: "Healed" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Quarantined" })).toBeInTheDocument();
  });
});
