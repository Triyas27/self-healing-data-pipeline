import { useEffect, useState, type KeyboardEvent } from "react";
import { Link, useParams } from "react-router-dom";
import ChipList from "../components/ChipList";
import QuarantineTable from "../components/QuarantineTable";
import StatTile from "../components/StatTile";
import { useToast } from "../components/Toast";
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

interface AuditPatternGroup {
  key: string;
  outcome: string;
  transformChosen: string | null;
  diagnosisSource: string;
  sampleHypothesis: string | null;
  sampleReasoning: string | null;
  rows: [string, AuditEntry[]][];
}

// Groups rows by their final outcome + transform, not by row identifier, so a
// run with hundreds of near-identical rows collapses into a handful of
// scannable patterns instead of one wall-of-text block per row. Grouped by
// outcome/transform rather than the hypothesis/reasoning text itself, since
// LLM-diagnosed rows phrase the same underlying issue slightly differently
// from row to row -- that would fragment the groups right back into
// one-per-row for anything LLM-diagnosed.
function groupByPattern(entries: AuditEntry[]): AuditPatternGroup[] {
  const rowGroups = groupByRow(entries);
  const patternMap = new Map<string, AuditPatternGroup>();

  for (const [rowIdentifier, attempts] of rowGroups) {
    const last = attempts[attempts.length - 1];
    const key = `${last.outcome}::${last.transform_chosen ?? "none"}`;
    let group = patternMap.get(key);
    if (!group) {
      group = {
        key,
        outcome: last.outcome,
        transformChosen: last.transform_chosen,
        diagnosisSource: last.diagnosis_source,
        sampleHypothesis: last.hypothesis,
        sampleReasoning: last.reasoning,
        rows: [],
      };
      patternMap.set(key, group);
    }
    group.rows.push([rowIdentifier, attempts]);
  }

  return Array.from(patternMap.values()).sort((a, b) => b.rows.length - a.rows.length);
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);

  const [run, setRun] = useState<RunSummary | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [quarantineRows, setQuarantineRows] = useState<QuarantineRow[]>([]);
  const [quarantineTotal, setQuarantineTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const { showSuccess, showError } = useToast();

  function toggleGroup(key: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function handleGroupKeyDown(e: KeyboardEvent<HTMLDivElement>, key: string) {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleGroup(key);
    }
  }

  async function refreshQuarantine() {
    const page = await listQuarantine({ run_id: runId, limit: 500 });
    setQuarantineRows(page.items);
    setQuarantineTotal(page.total);
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
    try {
      await resolveQuarantineRow(quarantineId);
      showSuccess(`Row #${quarantineId} resolved.`);
      await refreshQuarantine();
    } catch (err) {
      showError(err instanceof Error ? err.message : `Failed to resolve row #${quarantineId}.`);
    }
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

  const patternGroups = groupByPattern(audit);

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
          <StatTile label="Rows" value={String(run.row_count)} tooltip="Total rows in this run." />
          <StatTile
            label="Clean first pass"
            value={String(run.clean_first_pass)}
            tooltip="Rows that passed validation with no repair needed."
          />
          <StatTile
            label="Healed"
            value={String(run.healed)}
            tooltip="Rows that failed validation but were automatically repaired."
          />
          <StatTile
            label="Quarantined"
            value={String(run.quarantined)}
            tooltip="Rows that failed validation and couldn't be safely repaired."
          />
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
        {patternGroups.length === 0 ? (
          <div className="empty-state">Every row in this run validated cleanly. Nothing to diagnose.</div>
        ) : (
          patternGroups.map((group) => {
            const isExpanded = expandedGroups.has(group.key);
            return (
              <div className="audit-group" key={group.key}>
                <div
                  className="audit-group-header expandable-row"
                  tabIndex={0}
                  role="button"
                  aria-expanded={isExpanded}
                  onClick={() => toggleGroup(group.key)}
                  onKeyDown={(e) => handleGroupKeyDown(e, group.key)}
                >
                  <span className={`badge ${outcomeBadgeClass(group.outcome)}`}>
                    {humanizeLabel(group.outcome)}
                  </span>{" "}
                  {group.transformChosen && (
                    <>
                      <span className="transform applied">{humanizeLabel(group.transformChosen)}</span>{" "}
                    </>
                  )}
                  <strong>
                    {group.rows.length} row{group.rows.length === 1 ? "" : "s"}
                  </strong>
                  <span className="muted"> &middot; {group.diagnosisSource}</span>
                </div>
                {group.sampleHypothesis && <div className="muted">{group.sampleHypothesis}</div>}
                {group.sampleReasoning && <div className="muted">{group.sampleReasoning}</div>}
                {isExpanded && (
                  <div className="audit-group-rows">
                    {group.rows.map(([rowIdentifier, attempts]) => (
                      <div key={rowIdentifier} style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 600, marginBottom: 8 }}>{rowIdentifier}</div>
                        {attempts.map((attempt, i) => (
                          <div className="attempt" key={attempt.id}>
                            <div>
                              attempt {i + 1} &middot; <span className="muted">{attempt.diagnosis_source}</span>{" "}
                              &middot;{" "}
                              <span className={`badge ${outcomeBadgeClass(attempt.outcome)}`}>
                                {humanizeLabel(attempt.outcome)}
                              </span>
                              {attempt.transform_chosen && (
                                <>
                                  {" "}
                                  <span className="transform applied">
                                    {humanizeLabel(attempt.transform_chosen)}
                                  </span>
                                </>
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
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="panel">
        <h2>Quarantined rows from this run</h2>
        {quarantineRows.length === 0 ? (
          <div className="empty-state">No quarantined rows from this run.</div>
        ) : (
          <>
            <QuarantineTable rows={quarantineRows} onResolve={handleResolve} />
            {quarantineTotal > quarantineRows.length && (
              <div className="muted" style={{ marginTop: 12 }}>
                Showing {quarantineRows.length} of {quarantineTotal} quarantined rows.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
