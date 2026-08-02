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
  const [counts, setCounts] = useState<Record<Filter, number>>({ unresolved: 0, resolved: 0, all: 0 });
  const [filter, setFilter] = useState<Filter>("unresolved");
  const [loading, setLoading] = useState(true);
  const { showSuccess, showError } = useToast();

  async function refresh(currentFilter: Filter) {
    setLoading(true);
    const resolved = currentFilter === "all" ? undefined : currentFilter === "resolved";
    // Counts for all three tabs are fetched alongside the current page so the
    // tab labels always reflect reality, not just whichever filter is active.
    const [data, unresolvedCount, resolvedCount, allCount] = await Promise.all([
      listQuarantine({ resolved, limit: FETCH_LIMIT }),
      listQuarantine({ resolved: false, limit: 1 }),
      listQuarantine({ resolved: true, limit: 1 }),
      listQuarantine({ limit: 1 }),
    ]);
    setRows(data.items);
    setTotal(data.total);
    setCounts({ unresolved: unresolvedCount.total, resolved: resolvedCount.total, all: allCount.total });
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
              {f} ({counts[f]})
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
