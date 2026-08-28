import type { ZoneScore, ZoneSignals } from "../types";

interface SignalsPanelProps {
  zones: ZoneScore[];
}

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function averageSignal(zones: ZoneScore[], key: keyof ZoneSignals): number {
  return Math.round(average(zones.map((z) => z.signals[key])) * 100);
}

export default function SignalsPanel({ zones }: SignalsPanelProps) {
  const rows: Array<{ label: string; value: number }> = [
    { label: "Traffic", value: averageSignal(zones, "traffic_congestion") },
    { label: "Transit", value: averageSignal(zones, "transit_delay") },
    { label: "Weather", value: averageSignal(zones, "weather_severity") },
    { label: "Events", value: averageSignal(zones, "event_density") },
  ];

  return (
    <section className="panel signals">
      <p className="eyebrow">CITY SIGNALS</p>
      {rows.map((row) => (
        <div className="signal" key={row.label}>
          <span>{row.label}</span>
          <strong>{row.value}</strong>
          <div className="bar">
            <i style={{ width: `${row.value}%` }} />
          </div>
        </div>
      ))}
    </section>
  );
}
