interface StatTileProps {
  label: string;
  value: string;
}

export default function StatTile({ label, value }: StatTileProps) {
  return (
    <div className="stat-tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}
