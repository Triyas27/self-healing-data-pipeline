import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HealRatePoint } from "../api/types";

interface HealRateChartProps {
  data: HealRatePoint[];
}

export default function HealRateChart({ data }: HealRateChartProps) {
  if (data.length === 0) {
    return <div className="empty-state">No completed runs yet.</div>;
  }

  const chartData = data.map((point) => ({
    run: `#${point.run_id}`,
    healRate: Math.round(point.heal_rate * 1000) / 10,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3d" />
        <XAxis dataKey="run" stroke="#9aa0ac" fontSize={12} />
        <YAxis stroke="#9aa0ac" fontSize={12} domain={[0, 100]} unit="%" />
        <Tooltip
          contentStyle={{ background: "#1b1f2a", border: "1px solid #2a2f3d", borderRadius: 8, fontSize: 13 }}
          formatter={(value: number) => [`${value}%`, "Heal rate"]}
        />
        <Line type="monotone" dataKey="healRate" stroke="#5b8cff" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
