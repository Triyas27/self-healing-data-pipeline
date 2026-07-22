import { Fragment, useState, type KeyboardEvent } from "react";
import type { QuarantineRow } from "../api/types";

interface QuarantineTableProps {
  rows: QuarantineRow[];
  onResolve: (id: number) => void;
}

export default function QuarantineTable({ rows, onResolve }: QuarantineTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (rows.length === 0) {
    return <div className="empty-state">No quarantined rows match this filter.</div>;
  }

  function toggleExpanded(id: number) {
    setExpandedId(expandedId === id ? null : id);
  }

  function handleRowKeyDown(e: KeyboardEvent<HTMLTableRowElement>, id: number) {
    // Ignore keydowns bubbling up from focusable descendants (e.g. the Resolve button)
    // so activating that button doesn't also toggle the row.
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
          <th>ID</th>
          <th>Run</th>
          <th>Error type</th>
          <th>Attempts</th>
          <th>Resolved</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Fragment key={row.id}>
            <tr
              className="quarantine-row"
              tabIndex={0}
              role="button"
              aria-expanded={expandedId === row.id}
              onClick={() => toggleExpanded(row.id)}
              onKeyDown={(e) => handleRowKeyDown(e, row.id)}
            >
              <td>#{row.id}</td>
              <td>#{row.run_id}</td>
              <td>{row.error_type}</td>
              <td>{row.attempt_count}</td>
              <td>
                <span className={`badge resolved-${row.resolved}`}>{row.resolved ? "resolved" : "unresolved"}</span>
              </td>
              <td>
                {!row.resolved && (
                  <button
                    className="secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      onResolve(row.id);
                    }}
                  >
                    Resolve
                  </button>
                )}
              </td>
            </tr>
            {expandedId === row.id && (
              <tr>
                <td colSpan={6}>
                  <div className="detail-panel">
                    <div className="muted">{row.error_detail}</div>
                    <pre>{JSON.stringify(row.original_data, null, 2)}</pre>
                    <div>
                      {row.diagnosis_history.map((attempt, i) => (
                        <div className="attempt" key={i}>
                          <div>
                            attempt {i + 1} &middot; <span className="muted">{attempt.source}</span> &middot;{" "}
                            <span className={`transform ${attempt.transform ? "applied" : "no-fix"}`}>
                              {attempt.transform ?? "no_fix"}
                            </span>{" "}
                            <span className="muted">(confidence {attempt.confidence.toFixed(2)})</span>
                          </div>
                          <div className="muted">{attempt.hypothesis}</div>
                          <div className="muted">{attempt.reasoning}</div>
                        </div>
                      ))}
                    </div>
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
