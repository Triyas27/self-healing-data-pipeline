import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HealRatePoint } from "../api/types";

interface HealRateChartProps {
  data: HealRatePoint[];
}

interface ChartPoint {
  run: string;
  healRate: number;
  rowCount: number;
}

interface TooltipPayloadEntry {
  payload: ChartPoint;
}

export function HealRateTooltipContent({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
}) {
  if (!active || !payload?.length) {
    return null;
  }
  const point = payload[0].payload;
  return (
    <div style={{ background: "#1b1f2a", border: "1px solid #2a2f3d", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>
      <div>{point.run}</div>
      <div>{point.healRate}% heal rate</div>
      <div style={{ color: "#9aa0ac" }}>{point.rowCount} rows</div>
    </div>
  );
}

export default function HealRateChart({ data }: HealRateChartProps) {
  if (data.length === 0) {
    return <div className="empty-state">No completed runs yet.</div>;
  }

  const chartData: ChartPoint[] = data.map((point) => ({
    run: `#${point.run_id}`,
    healRate: Math.round(point.heal_rate * 1000) / 10,
    rowCount: point.row_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3d" />
        <XAxis dataKey="run" stroke="#9aa0ac" fontSize={12} />
        <YAxis stroke="#9aa0ac" fontSize={12} domain={[0, 100]} unit="%" />
        <Tooltip content={<HealRateTooltipContent />} />
        <Line type="monotone" dataKey="healRate" stroke="#5b8cff" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
