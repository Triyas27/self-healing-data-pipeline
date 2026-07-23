import { humanizeLabel } from "../utils/labels";

interface ChipListProps {
  counts: Record<string, number>;
  emptyLabel: string;
}

export default function ChipList({ counts, emptyLabel }: ChipListProps) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return <div className="muted">{emptyLabel}</div>;
  }
  return (
    <div className="chip-list">
      {entries.map(([label, count]) => (
        <span className="chip" key={label}>
          {humanizeLabel(label)} <span className="count">&times;{count}</span>
        </span>
      ))}
    </div>
  );
}
