import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef } from "react";

import type { ZoneScore } from "../types";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN ?? "";

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

function addZoneLayers(map: mapboxgl.Map) {
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

  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false });

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
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [-73.9857, 40.7484],
      zoom: 11,
    });
    mapRef.current = map;

    map.on("load", () => {
      loadedRef.current = true;
      addZoneLayers(map);
      const source = map.getSource(ZONES_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
      source?.setData(toFeatureCollection(zones));
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
    const source = map.getSource(ZONES_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
    source?.setData(toFeatureCollection(zones));
  }, [zones]);

  if (!MAPBOX_TOKEN) {
    return (
      <div style={{ padding: "1rem" }}>
        Set <code>VITE_MAPBOX_TOKEN</code> in <code>frontend/.env</code> to render the map.
      </div>
    );
  }

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
