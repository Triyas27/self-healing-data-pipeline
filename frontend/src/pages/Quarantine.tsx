import { useEffect, useState } from "react";
import QuarantineTable from "../components/QuarantineTable";
import { listQuarantine, resolveQuarantineRow } from "../api/client";
import type { QuarantineRow } from "../api/types";

type Filter = "all" | "unresolved" | "resolved";

export default function Quarantine() {
  const [rows, setRows] = useState<QuarantineRow[]>([]);
  const [filter, setFilter] = useState<Filter>("unresolved");
  const [loading, setLoading] = useState(true);

  async function refresh(currentFilter: Filter) {
    setLoading(true);
    const resolved = currentFilter === "all" ? undefined : currentFilter === "resolved";
    const data = await listQuarantine({ resolved });
    setRows(data);
    setLoading(false);
  }

  useEffect(() => {
    refresh(filter);
  }, [filter]);

  async function handleResolve(id: number) {
    await resolveQuarantineRow(id);
    refresh(filter);
  }

  return (
    <div>
      <div className="panel">
        <h2>Quarantined rows</h2>
        <div className="filters">
          {(["unresolved", "resolved", "all"] as Filter[]).map((f) => (
            <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>
              {f}
            </button>
          ))}
        </div>
        {loading ? <div className="empty-state">Loading...</div> : <QuarantineTable rows={rows} onResolve={handleResolve} />}
      </div>
    </div>
  );
}
