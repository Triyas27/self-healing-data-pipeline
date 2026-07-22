import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { humanizeLabel } from "../utils/labels";

interface ErrorBreakdownChartProps {
  errorTypeTotals: Record<string, number>;
  fixesAppliedTotals: Record<string, number>;
}

const MAX_BARS = 8;

function toChartData(totals: Record<string, number>) {
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_BARS)
    .map(([key, count]) => ({ label: humanizeLabel(key), count }));
}

function BreakdownBars({ data, color, emptyLabel }: { data: { label: string; count: number }[]; color: string; emptyLabel: string }) {
  if (data.length === 0) {
    return <div className="empty-state">{emptyLabel}</div>;
  }
  const height = Math.max(80, data.length * 32);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3d" horizontal={false} />
        <XAxis type="number" stroke="#9aa0ac" fontSize={12} allowDecimals={false} />
        <YAxis type="category" dataKey="label" stroke="#9aa0ac" fontSize={12} width={140} />
        <Tooltip
          contentStyle={{ background: "#1b1f2a", border: "1px solid #2a2f3d", borderRadius: 8, fontSize: 13 }}
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
        />
        <Bar dataKey="count" fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function ErrorBreakdownChart({ errorTypeTotals, fixesAppliedTotals }: ErrorBreakdownChartProps) {
  const errorData = toChartData(errorTypeTotals);
  const fixData = toChartData(fixesAppliedTotals);

  return (
    <div className="detail-columns">
      <div>
        <h4>Error types (all runs)</h4>
        <BreakdownBars data={errorData} color="#e35d5d" emptyLabel="No validation errors recorded yet." />
      </div>
      <div>
        <h4>Fixes applied (all runs)</h4>
        <BreakdownBars data={fixData} color="#3ecf8e" emptyLabel="No automated fixes recorded yet." />
      </div>
    </div>
  );
}
