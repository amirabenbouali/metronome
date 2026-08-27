export interface ZoneSignals {
  traffic_congestion: number;
  transit_delay: number;
  weather_severity: number;
  event_density: number;
}

export interface ZoneScore {
  id: string;
  name: string;
  score: number;
  signals: ZoneSignals;
  geometry: GeoJSON.Geometry;
}
