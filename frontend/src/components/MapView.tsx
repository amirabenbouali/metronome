import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import type { ZoneScore } from "../types";

// Free, no-signup vector tiles + style. See https://openfreemap.org
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const ZONES_SOURCE_ID = "zones";

function toFeatureCollection(zones: ZoneScore[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: zones.map((zone) => ({
      type: "Feature",
      geometry: zone.geometry,
      properties: {
        id: zone.id,
        name: zone.name,
        score: zone.score,
        traffic_congestion: zone.signals.traffic_congestion,
        transit_delay: zone.signals.transit_delay,
        weather_severity: zone.signals.weather_severity,
        event_density: zone.signals.event_density,
      },
    })),
  };
}

function addZoneLayers(map: maplibregl.Map) {
  if (map.getSource(ZONES_SOURCE_ID)) return;

  map.addSource(ZONES_SOURCE_ID, {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });

  map.addLayer({
    id: "zones-fill",
    type: "fill",
    source: ZONES_SOURCE_ID,
    paint: {
      "fill-color": [
        "interpolate",
        ["linear"],
        ["get", "score"],
        0,
        "#2166ac",
        25,
        "#67a9cf",
        50,
        "#fee090",
        75,
        "#fc8d59",
        100,
        "#b2182b",
      ],
      "fill-opacity": 0.6,
    },
  });

  map.addLayer({
    id: "zones-outline",
    type: "line",
    source: ZONES_SOURCE_ID,
    paint: {
      "line-color": "#ffffff",
      "line-width": 1,
    },
  });

  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

  map.on("mousemove", "zones-fill", (e) => {
    map.getCanvas().style.cursor = "pointer";
    const feature = e.features?.[0];
    if (!feature || !e.lngLat) return;
    const p = feature.properties as Record<string, number | string>;
    popup
      .setLngLat(e.lngLat)
      .setHTML(
        `<strong>${p.name}</strong><br/>score: ${p.score}<br/>` +
          `traffic: ${p.traffic_congestion} · transit: ${p.transit_delay} · ` +
          `weather: ${p.weather_severity} · events: ${p.event_density}`,
      )
      .addTo(map);
  });

  map.on("mouseleave", "zones-fill", () => {
    map.getCanvas().style.cursor = "";
    popup.remove();
  });
}

interface MapViewProps {
  zones: ZoneScore[];
}

export default function MapView({ zones }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  // Always holds the latest zones, so the "load" handler (attached once,
  // long before the first real fetch resolves) never reads a stale closure.
  const zonesRef = useRef<ZoneScore[]>(zones);
  zonesRef.current = zones;

  const syncZones = (map: maplibregl.Map) => {
    const source = map.getSource(ZONES_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    source?.setData(toFeatureCollection(zonesRef.current));
  };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-73.9857, 40.7484],
      zoom: 11,
    });
    mapRef.current = map;

    map.on("load", () => {
      loadedRef.current = true;
      addZoneLayers(map);
      syncZones(map);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    syncZones(map);
  }, [zones]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
