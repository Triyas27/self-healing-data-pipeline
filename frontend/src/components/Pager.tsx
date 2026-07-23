interface PagerProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
}

export default function Pager({ total, limit, offset, onOffsetChange }: PagerProps) {
  if (total === 0) {
    return null;
  }

  const start = offset + 1;
  const end = Math.min(offset + limit, total);
  const hasPrevious = offset > 0;
  const hasNext = end < total;

  return (
    <div className="pager">
      <span className="muted">
        {start}&ndash;{end} of {total}
      </span>
      <button
        type="button"
        className="secondary"
        disabled={!hasPrevious}
        onClick={() => onOffsetChange(Math.max(0, offset - limit))}
      >
        Previous
      </button>
      <button type="button" className="secondary" disabled={!hasNext} onClick={() => onOffsetChange(offset + limit)}>
        Next
      </button>
    </div>
  );
}
