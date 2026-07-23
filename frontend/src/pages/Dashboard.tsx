import { useEffect, useState } from "react";
import ErrorBreakdownChart from "../components/ErrorBreakdownChart";
import HealRateChart from "../components/HealRateChart";
import Pager from "../components/Pager";
import RunsTable from "../components/RunsTable";
import StatTile from "../components/StatTile";
import TriggerRunForm from "../components/TriggerRunForm";
import { getStats, listRuns } from "../api/client";
import type { RunSummary, StatsOut } from "../api/types";

const RUNS_PAGE_SIZE = 10;

function pct(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

export default function Dashboard() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsTotal, setRunsTotal] = useState(0);
  const [runsOffset, setRunsOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  async function refresh(offset: number) {
    const [statsData, runsPage] = await Promise.all([getStats(), listRuns(RUNS_PAGE_SIZE, offset)]);
    setStats(statsData);
    setRuns(runsPage.items);
    setRunsTotal(runsPage.total);
    setLoading(false);
  }

  useEffect(() => {
    refresh(runsOffset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runsOffset]);

  function handleRunComplete() {
    setRunsOffset(0);
    refresh(0);
  }

  return (
    <div>
      <div className="stat-grid">
        <StatTile label="Rows processed" value={loading ? "..." : String(stats?.total_rows_processed ?? 0)} />
        <StatTile label="Overall heal rate" value={loading ? "..." : pct(stats?.overall_heal_rate ?? 0)} />
        <StatTile label="Auto-heal rate" value={loading ? "..." : pct(stats?.auto_heal_rate ?? 0)} />
        <StatTile label="Quarantined" value={loading ? "..." : String(stats?.total_quarantined ?? 0)} />
      </div>

      <div className="panel">
        <h2>Heal rate over time</h2>
        <HealRateChart data={stats?.heal_rate_over_time ?? []} />
      </div>

      <div className="panel">
        <h2>What's going wrong, and how it's getting fixed</h2>
        <ErrorBreakdownChart
          errorTypeTotals={stats?.error_type_totals ?? {}}
          fixesAppliedTotals={stats?.fixes_applied_totals ?? {}}
        />
      </div>

      <div className="panel">
        <h2>Trigger a run</h2>
        <TriggerRunForm onRunComplete={handleRunComplete} />
      </div>

      <div className="panel">
        <h2>Recent runs</h2>
        <RunsTable runs={runs} />
        <Pager total={runsTotal} limit={RUNS_PAGE_SIZE} offset={runsOffset} onOffsetChange={setRunsOffset} />
      </div>
    </div>
  );
}
