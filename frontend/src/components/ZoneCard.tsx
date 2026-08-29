import { scoreState, scoreStateColor } from "../lib/scoreState";
import type { ZoneScore } from "../types";

interface ZoneCardProps {
  zone: ZoneScore | null;
  delta: number | null;
}

function formatDelta(delta: number | null): string {
  if (delta === null) return "Watching for the next update…";
  if (delta === 0) return "No change since last update";
  const arrow = delta > 0 ? "↑" : "↓";
  return `${arrow} ${delta > 0 ? "+" : ""}${delta} since last update`;
}

export default function ZoneCard({ zone, delta }: ZoneCardProps) {
  if (!zone) {
    return (
      <section className="panel zonecard">
        <p className="eyebrow">FOCUSED ZONE</p>
        <h2>Select a zone</h2>
        <div className="driver">Click any zone on the map, or search above, to see its live breakdown.</div>
      </section>
    );
  }

  const state = scoreState(zone.score);
  const rows: Array<{ label: string; text: string }> = [
    { label: "Traffic", text: zone.details.traffic },
    { label: "Transit", text: zone.details.transit },
    { label: "Weather", text: zone.details.weather },
    { label: "Events", text: zone.details.events },
  ];

  return (
    <section className="panel zonecard">
      <p className="eyebrow">FOCUSED ZONE</p>
      <h2>{zone.name}</h2>
      <div className="scoreline">
        <strong>{Math.round(zone.score)}</strong>
        <span style={{ color: scoreStateColor(state) }}>{state}</span>
      </div>
      <div className="delta">{formatDelta(delta)}</div>
      <div className="detailgrid">
        {rows.map((row) => (
          <div className="detailrow" key={row.label}>
            <span>{row.label.toUpperCase()}</span>
            <p>{row.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
