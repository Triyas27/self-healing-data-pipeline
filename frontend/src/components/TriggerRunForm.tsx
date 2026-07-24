import { useRef, useState, type FormEvent } from "react";
import { useToast } from "./Toast";
import { triggerRun, triggerRunFromFile } from "../api/client";
import { FAILURE_MODES, type FailureMode, type RunSummary } from "../api/types";

interface TriggerRunFormProps {
  onRunComplete: (run: RunSummary) => void;
}

type Mode = "synthetic" | "upload";

export default function TriggerRunForm({ onRunComplete }: TriggerRunFormProps) {
  const [mode, setMode] = useState<Mode>("synthetic");
  const [rowCount, setRowCount] = useState(50);
  const [failureRate, setFailureRate] = useState(0.2);
  const [failureMode, setFailureMode] = useState<FailureMode | "">("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showSuccess } = useToast();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const run =
        mode === "upload" && file
          ? await triggerRunFromFile(file, false)
          : await triggerRun({
              row_count: rowCount,
              failure_rate: failureRate,
              failure_mode: failureMode || undefined,
              use_llm: false,
            });
      onRunComplete(run);
      showSuccess(`Run #${run.id} triggered — ${run.row_count} rows processed.`);
      if (mode === "upload") {
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger run");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error-banner">{error}</div>}
      <div className="filters" style={{ marginBottom: 16 }}>
        <button type="button" className={mode === "synthetic" ? "active" : ""} onClick={() => setMode("synthetic")}>
          Generate synthetic data
        </button>
        <button type="button" className={mode === "upload" ? "active" : ""} onClick={() => setMode("upload")}>
          Upload CSV
        </button>
      </div>

      {mode === "synthetic" ? (
        <div className="form-row">
          <div className="field">
            <label htmlFor="row-count">Row count</label>
            <input
              id="row-count"
              type="number"
              min={1}
              max={10000}
              value={rowCount}
              onChange={(e) => setRowCount(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="failure-rate">Failure rate</label>
            <input
              id="failure-rate"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={failureRate}
              onChange={(e) => setFailureRate(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="failure-mode">Failure mode</label>
            <select
              id="failure-mode"
              value={failureMode}
              onChange={(e) => setFailureMode(e.target.value as FailureMode | "")}
            >
              <option value="">Mixed (random)</option>
              {FAILURE_MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={submitting}>
            {submitting ? "Running..." : "Trigger run"}
          </button>
        </div>
      ) : (
        <div className="form-row">
          <div className="field">
            <label htmlFor="csv-file">CSV file</label>
            <input
              id="csv-file"
              type="file"
              accept=".csv,text/csv"
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              style={{ width: 220 }}
            />
          </div>
          <button type="submit" disabled={submitting || !file}>
            {submitting ? "Running..." : "Upload & run"}
          </button>
        </div>
      )}
    </form>
  );
}
