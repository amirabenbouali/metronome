export type LayerKey =
  | "score"
  | "traffic_congestion"
  | "transit_delay"
  | "weather_severity"
  | "event_density";

export const LAYER_OPTIONS: Array<{ key: LayerKey; label: string }> = [
  { key: "score", label: "Pulse score" },
  { key: "traffic_congestion", label: "Traffic" },
  { key: "transit_delay", label: "Transit" },
  { key: "weather_severity", label: "Weather" },
  { key: "event_density", label: "Events" },
];

export function layerLabel(key: LayerKey): string {
  return LAYER_OPTIONS.find((opt) => opt.key === key)?.label ?? "Pulse score";
}
