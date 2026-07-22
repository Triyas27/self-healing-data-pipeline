export function humanizeLabel(raw: string): string {
  const words = raw.split("_").map((word) => (word === "id" ? "ID" : word));
  const joined = words.join(" ");
  return joined.charAt(0).toUpperCase() + joined.slice(1);
}

export function formatHealTime(ms: number): string {
  if (ms === 0) return "0 ms/row";
  if (ms < 1) return `${ms.toFixed(2)} ms/row`;
  if (ms < 10) return `${ms.toFixed(1)} ms/row`;
  return `${Math.round(ms)} ms/row`;
}
