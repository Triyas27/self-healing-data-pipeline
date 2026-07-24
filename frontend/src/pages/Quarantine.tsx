import { useEffect, useState } from "react";
import Pager from "../components/Pager";
import QuarantineTable from "../components/QuarantineTable";
import { useToast } from "../components/Toast";
import { listQuarantine, resolveQuarantineRow } from "../api/client";
import type { QuarantineRow } from "../api/types";

type Filter = "all" | "unresolved" | "resolved";

const PAGE_SIZE = 15;

export default function Quarantine() {
  const [rows, setRows] = useState<QuarantineRow[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<Filter>("unresolved");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const { showSuccess, showError } = useToast();

  async function refresh(currentFilter: Filter, currentOffset: number) {
    setLoading(true);
    const resolved = currentFilter === "all" ? undefined : currentFilter === "resolved";
    const data = await listQuarantine({ resolved, limit: PAGE_SIZE, offset: currentOffset });
    setRows(data.items);
    setTotal(data.total);
    setLoading(false);
  }

  useEffect(() => {
    refresh(filter, offset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, offset]);

  function handleFilterChange(f: Filter) {
    setFilter(f);
    setOffset(0);
  }

  async function handleResolve(id: number) {
    try {
      await resolveQuarantineRow(id);
      showSuccess(`Row #${id} resolved.`);
      refresh(filter, offset);
    } catch (err) {
      showError(err instanceof Error ? err.message : `Failed to resolve row #${id}.`);
    }
  }

  return (
    <div>
      <div className="panel">
        <h2>Quarantined rows</h2>
        <div className="filters">
          {(["unresolved", "resolved", "all"] as Filter[]).map((f) => (
            <button key={f} className={filter === f ? "active" : ""} onClick={() => handleFilterChange(f)}>
              {f}
            </button>
          ))}
        </div>
        {loading ? <div className="empty-state">Loading...</div> : <QuarantineTable rows={rows} onResolve={handleResolve} />}
        <Pager total={total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
      </div>
    </div>
  );
}
