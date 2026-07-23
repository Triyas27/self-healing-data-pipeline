import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ChipList from "../components/ChipList";
import QuarantineTable from "../components/QuarantineTable";
import StatTile from "../components/StatTile";
import { getRun, getRunAudit, listQuarantine, resolveQuarantineRow } from "../api/client";
import type { AuditEntry, QuarantineRow, RunSummary } from "../api/types";
import { formatHealTime, humanizeLabel } from "../utils/labels";

function outcomeBadgeClass(outcome: string): string {
  if (outcome === "healed") return "completed";
  if (outcome === "no_fix") return "failed";
  return "running";
}

function groupByRow(entries: AuditEntry[]): [string, AuditEntry[]][] {
  const groups = new Map<string, AuditEntry[]>();
  for (const entry of entries) {
    const list = groups.get(entry.row_identifier) ?? [];
    list.push(entry);
    groups.set(entry.row_identifier, list);
  }
  return Array.from(groups.entries());
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);

  const [run, setRun] = useState<RunSummary | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [quarantineRows, setQuarantineRows] = useState<QuarantineRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  async function refreshQuarantine() {
    setQuarantineRows(await listQuarantine({ run_id: runId }));
  }

  useEffect(() => {
    async function load() {
      setLoading(true);
      setNotFound(false);
      try {
        const [runData, auditData] = await Promise.all([getRun(runId), getRunAudit(runId)]);
        setRun(runData);
        setAudit(auditData);
        await refreshQuarantine();
      } catch {
        setNotFound(true);
      } finally {
        setLoading(false);
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  async function handleResolve(quarantineId: number) {
    await resolveQuarantineRow(quarantineId);
    await refreshQuarantine();
  }

  if (loading) {
    return <div className="empty-state">Loading...</div>;
  }

  if (notFound || !run) {
    return (
      <div className="panel">
        <div className="empty-state">Run #{id} not found.</div>
        <Link to="/" className="detail-link">
          &larr; Back to dashboard
        </Link>
      </div>
    );
  }

  const rowGroups = groupByRow(audit);

  return (
    <div>
      <Link to="/" className="detail-link" style={{ marginBottom: 16 }}>
        &larr; Back to dashboard
      </Link>

      <div className="panel">
        <h2>
          Run #{run.id} <span className={`badge ${run.status}`}>{run.status}</span>
        </h2>
        <div className="muted" style={{ marginBottom: 16 }}>
          Started {new Date(run.started_at).toLocaleString()}
          {run.finished_at && ` · finished ${new Date(run.finished_at).toLocaleString()}`}
        </div>
        <div className="stat-grid">
          <StatTile label="Rows" value={String(run.row_count)} />
          <StatTile label="Clean first pass" value={String(run.clean_first_pass)} />
          <StatTile label="Healed" value={String(run.healed)} />
          <StatTile label="Quarantined" value={String(run.quarantined)} />
        </div>
        {run.avg_time_to_heal_ms !== null && (
          <div className="muted" style={{ marginTop: 12 }}>
            Avg time to heal: {formatHealTime(run.avg_time_to_heal_ms)}
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Error types &amp; fixes applied</h2>
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
      </div>

      <div className="panel">
        <h2>Audit trail</h2>
        {rowGroups.length === 0 ? (
          <div className="empty-state">Every row in this run validated cleanly — nothing to diagnose.</div>
        ) : (
          rowGroups.map(([rowIdentifier, attempts]) => (
            <div key={rowIdentifier} style={{ marginBottom: 20 }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>{rowIdentifier}</div>
              {attempts.map((attempt, i) => (
                <div className="attempt" key={attempt.id}>
                  <div>
                    attempt {i + 1} &middot; <span className="muted">{attempt.diagnosis_source}</span> &middot;{" "}
                    <span className={`badge ${outcomeBadgeClass(attempt.outcome)}`}>
                      {humanizeLabel(attempt.outcome)}
                    </span>{" "}
                    {attempt.transform_chosen && (
                      <span className="transform applied">{humanizeLabel(attempt.transform_chosen)}</span>
                    )}
                    {attempt.confidence !== null && (
                      <span className="muted"> (confidence {attempt.confidence.toFixed(2)})</span>
                    )}
                  </div>
                  {attempt.hypothesis && <div className="muted">{attempt.hypothesis}</div>}
                  {attempt.reasoning && <div className="muted">{attempt.reasoning}</div>}
                </div>
              ))}
            </div>
          ))
        )}
      </div>

      <div className="panel">
        <h2>Quarantined rows from this run</h2>
        {quarantineRows.length === 0 ? (
          <div className="empty-state">No quarantined rows from this run.</div>
        ) : (
          <QuarantineTable rows={quarantineRows} onResolve={handleResolve} />
        )}
      </div>
    </div>
  );
}
