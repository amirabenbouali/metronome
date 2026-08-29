export interface ZoneSignals {
  traffic_congestion: number;
  transit_delay: number;
  weather_severity: number;
  event_density: number;
}

export interface SignalDetails {
  traffic: string;
  transit: string;
  weather: string;
  events: string;
}

export interface ZoneScore {
  id: string;
  name: string;
  score: number;
  signals: ZoneSignals;
  details: SignalDetails;
  geometry: GeoJSON.Geometry;
}
