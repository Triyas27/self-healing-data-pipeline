import { useEffect, useState } from "react";
import QuarantineTable from "../components/QuarantineTable";
import { useToast } from "../components/Toast";
import { listQuarantine, resolveQuarantineRow } from "../api/client";
import type { QuarantineRow } from "../api/types";

type Filter = "all" | "unresolved" | "resolved";

// Grouping by error type needs the full filtered set in hand rather than one
// page at a time, so this fetches up to the backend's max page size instead
// of paginating. 500 comfortably covers this project's demo data volume.
const FETCH_LIMIT = 500;

export default function Quarantine() {
  const [rows, setRows] = useState<QuarantineRow[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<Filter>("unresolved");
  const [loading, setLoading] = useState(true);
  const { showSuccess, showError } = useToast();

  async function refresh(currentFilter: Filter) {
    setLoading(true);
    const resolved = currentFilter === "all" ? undefined : currentFilter === "resolved";
    const data = await listQuarantine({ resolved, limit: FETCH_LIMIT });
    setRows(data.items);
    setTotal(data.total);
    setLoading(false);
  }

  useEffect(() => {
    refresh(filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  function handleFilterChange(f: Filter) {
    setFilter(f);
  }

  async function handleResolve(id: number) {
    try {
      await resolveQuarantineRow(id);
      showSuccess(`Row #${id} resolved.`);
      refresh(filter);
    } catch (err) {
      showError(err instanceof Error ? err.message : `Failed to resolve row #${id}.`);
    }
  }

  return (
    <div>
      <div className="panel">
        <h2>Quarantined rows</h2>
        <p className="muted" style={{ marginTop: -8, marginBottom: 16 }}>
          Rows the pipeline couldn't safely auto-repair. Resolving one just marks it as reviewed by a
          human; it's a bookkeeping flag and doesn't change the underlying data or re-run the pipeline.
        </p>
        <div className="filters">
          {(["unresolved", "resolved", "all"] as Filter[]).map((f) => (
            <button key={f} className={filter === f ? "active" : ""} onClick={() => handleFilterChange(f)}>
              {f}
            </button>
          ))}
        </div>
        {loading ? (
          <div className="empty-state">Loading...</div>
        ) : (
          <QuarantineTable rows={rows} onResolve={handleResolve} groupByErrorType />
        )}
        {!loading && total > rows.length && (
          <div className="muted" style={{ marginTop: 12 }}>
            Showing {rows.length} of {total} quarantined rows.
          </div>
        )}
      </div>
    </div>
  );
}
