import type { ZoneSignals } from "../types";

const SIGNAL_LABELS: Record<keyof ZoneSignals, string> = {
  traffic_congestion: "Road congestion",
  transit_delay: "Transit delays",
  weather_severity: "Weather conditions",
  event_density: "Event activity",
};

/** A short human-readable sentence naming whichever signal(s) dominate a zone's score. */
export function primaryDriver(signals: ZoneSignals): string {
  const entries = (Object.entries(signals) as [keyof ZoneSignals, number][]).sort(
    (a, b) => b[1] - a[1],
  );
  const [topKey, topValue] = entries[0];
  const [secondKey, secondValue] = entries[1];

  if (topValue < 0.3) {
    return "Conditions are stable across all signals right now.";
  }

  if (secondValue >= 0.4 && topValue - secondValue < 0.2) {
    return `${SIGNAL_LABELS[topKey]} and ${SIGNAL_LABELS[secondKey].toLowerCase()} are both elevated.`;
  }

  return `${SIGNAL_LABELS[topKey]} is the main contributor.`;
}
