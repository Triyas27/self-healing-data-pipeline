import { useEffect, useState } from "react";
import ErrorBreakdownChart from "../components/ErrorBreakdownChart";
import HealRateChart from "../components/HealRateChart";
import RunsTable from "../components/RunsTable";
import StatTile from "../components/StatTile";
import TriggerRunForm from "../components/TriggerRunForm";
import { getStats, listRuns } from "../api/client";
import type { RunSummary, StatsOut } from "../api/types";

function pct(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

export default function Dashboard() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const [statsData, runsData] = await Promise.all([getStats(), listRuns(20)]);
    setStats(statsData);
    setRuns(runsData);
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

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
        <TriggerRunForm onRunComplete={refresh} />
      </div>

      <div className="panel">
        <h2>Recent runs</h2>
        <RunsTable runs={runs} />
      </div>
    </div>
  );
}
