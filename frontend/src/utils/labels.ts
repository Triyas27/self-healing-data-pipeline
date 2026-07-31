import type { RunSummary } from "../api/types";

export function humanizeLabel(raw: string): string {
  const words = raw.split("_").map((word) => (word === "id" ? "ID" : word));
  const joined = words.join(" ");
  return joined.charAt(0).toUpperCase() + joined.slice(1);
}

function topEntry(counts: Record<string, number>): [string, number] | null {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return entries[0] ?? null;
}

// One-line, plain-English gloss of what happened in a run -- meant to surface
// the "why" at the table-row level instead of requiring a click into the
// audit trail just to find out a run had any story to it at all.
export function summarizeRun(run: RunSummary): string {
  if (run.status === "rejected_schema_drift") {
    return "Batch rejected: unexpected column(s) in the CSV (schema drift).";
  }
  if (run.status === "failed") {
    return "Run failed unexpectedly partway through.";
  }
  if (run.status === "running") {
    return "Still running...";
  }

  const errorRowCount = run.healed + run.quarantined;
  if (errorRowCount === 0) {
    return `All ${run.row_count} rows clean, no repairs needed.`;
  }

  const topError = topEntry(run.error_types);
  const errorPhrase = topError ? `mostly ${humanizeLabel(topError[0]).toLowerCase()}` : "mixed causes";
  const parts = [`${errorRowCount} row${errorRowCount === 1 ? "" : "s"} had errors (${errorPhrase})`];

  if (run.healed > 0) {
    const topFix = topEntry(run.fixes_applied);
    const fixPhrase = topFix ? ` (mainly ${humanizeLabel(topFix[0]).toLowerCase()})` : "";
    parts.push(`${run.healed} auto-fixed${fixPhrase}`);
  }
  if (run.quarantined > 0) {
    parts.push(`${run.quarantined} quarantined`);
  }

  return `${parts.join(", ")}.`;
}

export function formatHealTime(ms: number): string {
  if (ms === 0) return "0 ms/row";
  if (ms < 1) return `${ms.toFixed(2)} ms/row`;
  if (ms < 10) return `${ms.toFixed(1)} ms/row`;
  return `${Math.round(ms)} ms/row`;
}
