import type { RunSummary } from "../api/types";

interface RunsTableProps {
  runs: RunSummary[];
}

export default function RunsTable({ runs }: RunsTableProps) {
  if (runs.length === 0) {
    return <div className="empty-state">No runs yet. Trigger one above.</div>;
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
          <tr key={run.id}>
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
        ))}
      </tbody>
    </table>
  );
}
