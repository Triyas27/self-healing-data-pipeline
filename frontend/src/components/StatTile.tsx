interface StatTileProps {
  label: string;
  value: string;
  tooltip?: string;
}

export default function StatTile({ label, value, tooltip }: StatTileProps) {
  return (
    <div className="stat-tile">
      <div className="label">
        {label}
        {tooltip && (
          <span className="info-icon" tabIndex={0} title={tooltip} aria-label={tooltip}>
            &#9432;
          </span>
        )}
      </div>
      <div className="value">{value}</div>
    </div>
  );
}
