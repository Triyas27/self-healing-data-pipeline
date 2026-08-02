import { Fragment, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import type { QuarantineRow } from "../api/types";
import { humanizeLabel } from "../utils/labels";

interface QuarantineTableProps {
  rows: QuarantineRow[];
  onResolve: (id: number) => void;
  groupByErrorType?: boolean;
}

interface ErrorTypeGroup {
  errorType: string;
  rows: QuarantineRow[];
}

function groupRowsByErrorType(rows: QuarantineRow[]): ErrorTypeGroup[] {
  const groups = new Map<string, QuarantineRow[]>();
  for (const row of rows) {
    const list = groups.get(row.error_type) ?? [];
    list.push(row);
    groups.set(row.error_type, list);
  }
  return Array.from(groups.entries())
    .map(([errorType, groupRows]) => ({ errorType, rows: groupRows }))
    .sort((a, b) => b.rows.length - a.rows.length);
}

export default function QuarantineTable({ rows, onResolve, groupByErrorType }: QuarantineTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  if (rows.length === 0) {
    return <div className="empty-state">No quarantined rows match this filter.</div>;
  }

  function toggleExpanded(id: number) {
    setExpandedId(expandedId === id ? null : id);
  }

  function toggleGroup(errorType: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(errorType)) {
        next.delete(errorType);
      } else {
        next.add(errorType);
      }
      return next;
    });
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

  function handleGroupKeyDown(e: KeyboardEvent<HTMLDivElement>, errorType: string) {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleGroup(errorType);
    }
  }

  function renderTable(rowsToRender: QuarantineRow[]) {
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
          {rowsToRender.map((row) => (
            <Fragment key={row.id}>
              <tr
                className="expandable-row"
                tabIndex={0}
                role="button"
                aria-expanded={expandedId === row.id}
                onClick={() => toggleExpanded(row.id)}
                onKeyDown={(e) => handleRowKeyDown(e, row.id)}
              >
                <td>#{row.id}</td>
                <td>
                  <Link to={`/runs/${row.run_id}`} className="run-link" onClick={(e) => e.stopPropagation()}>
                    #{row.run_id}
                  </Link>
                </td>
                <td>{humanizeLabel(row.error_type)}</td>
                <td>{row.attempt_count}</td>
                <td>
                  <span className={`badge resolved-${row.resolved}`}>
                    {row.resolved ? "resolved" : "unresolved"}
                  </span>
                </td>
                <td>
                  {!row.resolved && (
                    <button
                      className="secondary"
                      title="Marks this row as reviewed by a human. Doesn't change the data or re-run the pipeline."
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
                                {attempt.transform ? humanizeLabel(attempt.transform) : "No fix"}
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

  if (!groupByErrorType) {
    return renderTable(rows);
  }

  const groups = groupRowsByErrorType(rows);

  return (
    <div>
      {groups.map((group) => {
        const isExpanded = expandedGroups.has(group.errorType);
        const unresolvedCount = group.rows.filter((row) => !row.resolved).length;
        return (
          <div className="quarantine-group" key={group.errorType}>
            <div
              className="quarantine-group-header expandable-row"
              tabIndex={0}
              role="button"
              aria-expanded={isExpanded}
              onClick={() => toggleGroup(group.errorType)}
              onKeyDown={(e) => handleGroupKeyDown(e, group.errorType)}
            >
              <strong>{humanizeLabel(group.errorType)}</strong>{" "}
              <span className="muted">
                {group.rows.length} row{group.rows.length === 1 ? "" : "s"}
              </span>
              {unresolvedCount > 0 && <span className="muted"> &middot; {unresolvedCount} unresolved</span>}
            </div>
            {isExpanded && <div className="quarantine-group-rows">{renderTable(group.rows)}</div>}
          </div>
        );
      })}
    </div>
  );
}
