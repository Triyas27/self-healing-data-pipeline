import { Fragment, useState, type KeyboardEvent } from "react";
import type { RunSummary } from "../api/types";

interface RunsTableProps {
  runs: RunSummary[];
}

function ChipList({ counts, emptyLabel }: { counts: Record<string, number>; emptyLabel: string }) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return <div className="muted">{emptyLabel}</div>;
  }
  return (
    <div className="chip-list">
      {entries.map(([label, count]) => (
        <span className="chip" key={label}>
          {label} <span className="count">&times;{count}</span>
        </span>
      ))}
    </div>
  );
}

export default function RunsTable({ runs }: RunsTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (runs.length === 0) {
    return <div className="empty-state">No runs yet. Trigger one above.</div>;
  }

  function toggleExpanded(id: number) {
    setExpandedId(expandedId === id ? null : id);
  }

  function handleRowKeyDown(e: KeyboardEvent<HTMLTableRowElement>, id: number) {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleExpanded(id);
    }
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Run</th>
          <th>Started</th>
          <th>Rows</th>
          <th>Clean</th>
          <th>Healed</th>
          <th>Quarantined</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <Fragment key={run.id}>
            <tr
              className="expandable-row"
              tabIndex={0}
              role="button"
              aria-expanded={expandedId === run.id}
              onClick={() => toggleExpanded(run.id)}
              onKeyDown={(e) => handleRowKeyDown(e, run.id)}
            >
              <td>#{run.id}</td>
              <td className="muted">{new Date(run.started_at).toLocaleString()}</td>
              <td>{run.row_count}</td>
              <td>{run.clean_first_pass}</td>
              <td>{run.healed}</td>
              <td>{run.quarantined}</td>
              <td>
                <span className={`badge ${run.status}`}>{run.status}</span>
              </td>
            </tr>
            {expandedId === run.id && (
              <tr>
                <td colSpan={7}>
                  <div className="detail-panel">
                    <div className="detail-columns">
                      <div>
                        <h4>Error types</h4>
                        <ChipList counts={run.error_types} emptyLabel="No validation errors on this run." />
                      </div>
                      <div>
                        <h4>Fixes applied</h4>
                        <ChipList counts={run.fixes_applied} emptyLabel="No automated fixes were needed." />
                      </div>
                    </div>
                    {run.avg_time_to_heal_ms !== null && (
                      <div className="muted" style={{ marginTop: 12 }}>
                        Avg time to heal: {run.avg_time_to_heal_ms.toFixed(1)} ms/row
                      </div>
                    )}
                  </div>
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}
