import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import type { LayerKey } from "../lib/layers";
import type { ZoneScore } from "../types";

// Free, no-signup vector tiles + style. See https://openfreemap.org
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const ZONES_SOURCE_ID = "zones";
const NO_SELECTION_FILTER: maplibregl.FilterSpecification = ["==", ["get", "id"], "__none__"];

function toFeatureCollection(zones: ZoneScore[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: zones.map((zone) => ({
      type: "Feature",
      id: zone.id,
      geometry: zone.geometry,
      properties: {
        id: zone.id,
        name: zone.name,
        score: zone.score,
        // Signals are 0-1; scale to 0-100 so every layer can share one
        // fill-color expression regardless of which property it reads.
        traffic_congestion: zone.signals.traffic_congestion * 100,
        transit_delay: zone.signals.transit_delay * 100,
        weather_severity: zone.signals.weather_severity * 100,
        event_density: zone.signals.event_density * 100,
      },
    })),
  };
}

function fillColorExpression(layer: LayerKey): maplibregl.ExpressionSpecification {
  return [
    "interpolate",
    ["linear"],
    ["get", layer],
    0,
    "#90f7b4",
    45,
    "#79afff",
    60,
    "#f4c06a",
    70,
    "#ff9a72",
    100,
    "#ff6c6c",
  ];
}

function addZoneLayers(map: maplibregl.Map, onSelectZone: (id: string) => void) {
  if (map.getSource(ZONES_SOURCE_ID)) return;

  map.addSource(ZONES_SOURCE_ID, {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
    promoteId: "id",
  });

  map.addLayer({
    id: "zones-fill",
    type: "fill",
    source: ZONES_SOURCE_ID,
    paint: {
      "fill-color": fillColorExpression("score"),
      "fill-opacity": [
        "case",
        ["boolean", ["feature-state", "hover"], false],
        0.85,
        0.55,
      ],
    },
  });

  map.addLayer({
    id: "zones-outline",
    type: "line",
    source: ZONES_SOURCE_ID,
    paint: {
      "line-color": "rgba(255,255,255,0.25)",
      "line-width": 1,
    },
  });

  map.addLayer({
    id: "zones-selected-outline",
    type: "line",
    source: ZONES_SOURCE_ID,
    filter: NO_SELECTION_FILTER,
    paint: {
      "line-color": "rgba(255,255,255,0.85)",
      "line-width": 2.5,
    },
  });

  let hoveredId: string | number | null = null;

  map.on("mousemove", "zones-fill", (e) => {
    map.getCanvas().style.cursor = "pointer";
    const feature = e.features?.[0];
    if (!feature || feature.id === undefined) return;
    if (hoveredId !== null && hoveredId !== feature.id) {
      map.setFeatureState({ source: ZONES_SOURCE_ID, id: hoveredId }, { hover: false });
    }
    hoveredId = feature.id;
    map.setFeatureState({ source: ZONES_SOURCE_ID, id: hoveredId }, { hover: true });
  });

  map.on("mouseleave", "zones-fill", () => {
    map.getCanvas().style.cursor = "";
    if (hoveredId !== null) {
      map.setFeatureState({ source: ZONES_SOURCE_ID, id: hoveredId }, { hover: false });
      hoveredId = null;
    }
  });

  map.on("click", "zones-fill", (e) => {
    const feature = e.features?.[0];
    const id = feature?.properties?.id;
    if (typeof id === "string") onSelectZone(id);
  });
}

interface MapViewProps {
  zones: ZoneScore[];
  selectedZoneId: string | null;
  onSelectZone: (id: string) => void;
  activeLayer: LayerKey;
}

export default function MapView({ zones, selectedZoneId, onSelectZone, activeLayer }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  // All three refs below exist for the same reason: each corresponding prop
  // can change (via data fetch, auto-selection, or a rail click) before the
  // map's "load" event ever fires, since that's gated on slow tile/style
  // network requests. Without a ref, the prop-driven effects below would
  // run-and-bail while loadedRef is still false and never get another
  // chance to apply once the map actually becomes ready.
  const zonesRef = useRef<ZoneScore[]>(zones);
  zonesRef.current = zones;
  const onSelectZoneRef = useRef(onSelectZone);
  onSelectZoneRef.current = onSelectZone;
  const selectedZoneIdRef = useRef<string | null>(selectedZoneId);
  selectedZoneIdRef.current = selectedZoneId;
  const activeLayerRef = useRef<LayerKey>(activeLayer);
  activeLayerRef.current = activeLayer;

  const syncZones = (map: maplibregl.Map) => {
    const source = map.getSource(ZONES_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    source?.setData(toFeatureCollection(zonesRef.current));
  };

  const syncSelection = (map: maplibregl.Map) => {
    const id = selectedZoneIdRef.current;
    map.setFilter("zones-selected-outline", id ? ["==", ["get", "id"], id] : NO_SELECTION_FILTER);
  };

  const syncLayer = (map: maplibregl.Map) => {
    map.setPaintProperty("zones-fill", "fill-color", fillColorExpression(activeLayerRef.current));
  };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-0.1, 51.51],
      zoom: 11,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.on("load", () => {
      loadedRef.current = true;
      addZoneLayers(map, (id) => onSelectZoneRef.current(id));
      syncZones(map);
      syncSelection(map);
      syncLayer(map);
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    syncSelection(map);
  }, [selectedZoneId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    syncLayer(map);
  }, [activeLayer]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
