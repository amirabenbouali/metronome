import { useCallback, useEffect, useRef, useState } from "react";

import Legend from "./components/Legend";
import MapView from "./components/MapView";
import Rail from "./components/Rail";
import SignalsPanel from "./components/SignalsPanel";
import Timestamp from "./components/Timestamp";
import Toast from "./components/Toast";
import ZoneCard from "./components/ZoneCard";
import { getZones } from "./lib/api";
import { layerLabel, type LayerKey } from "./lib/layers";
import { scoreState, scoreStateColor } from "./lib/scoreState";
import type { ZoneScore } from "./types";

const POLL_INTERVAL_MS = 30_000;
const TOAST_DURATION_MS = 1100;

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

export default function App() {
  const [zones, setZones] = useState<ZoneScore[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [toastMessage, setToastMessage] = useState("");
  const [toastVisible, setToastVisible] = useState(false);
  const [activeLayer, setActiveLayer] = useState<LayerKey>("score");
  const [signalsPanelVisible, setSignalsPanelVisible] = useState(true);

  // Previous poll's zones, one step behind `zones` - used to derive deltas.
  const previousZonesRef = useRef<ZoneScore[]>([]);
  const currentZonesRef = useRef<ZoneScore[]>([]);
  const selectedZoneIdRef = useRef<string | null>(null);
  selectedZoneIdRef.current = selectedZoneId;
  const toastTimeoutRef = useRef<number | undefined>(undefined);

  const refresh = useCallback(async () => {
    try {
      const next = await getZones();
      previousZonesRef.current = currentZonesRef.current;
      currentZonesRef.current = next;
      setZones(next);
      setLastUpdated(new Date());

      if (!selectedZoneIdRef.current && next.length > 0) {
        const top = [...next].sort((a, b) => b.score - a.score)[0];
        setSelectedZoneId(top.id);
      }
    } catch {
      // Keep showing the last-known state; the timestamp will just age.
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const handleSelectZone = useCallback((id: string) => {
    setSelectedZoneId(id);
    const zone = currentZonesRef.current.find((z) => z.id === id);
    setToastMessage(`${zone?.name ?? "Zone"} focused`);
    setToastVisible(true);
    window.clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = window.setTimeout(() => setToastVisible(false), TOAST_DURATION_MS);
  }, []);

  const selectedZone = zones.find((z) => z.id === selectedZoneId) ?? null;
  const previousSelectedZone = previousZonesRef.current.find((z) => z.id === selectedZoneId);
  const delta =
    selectedZone && previousSelectedZone
      ? Math.round(selectedZone.score - previousSelectedZone.score)
      : null;

  const globalScore = zones.length > 0 ? Math.round(average(zones.map((z) => z.score))) : null;
  const globalState = globalScore !== null ? scoreState(globalScore) : null;

  const alertZones = zones
    .filter((z) => {
      const state = scoreState(z.score);
      return state === "BUSY" || state === "INTENSE";
    })
    .sort((a, b) => b.score - a.score);

  return (
    <div className="app">
      <Rail
        live={zones.length > 0}
        activeLayer={activeLayer}
        onChangeLayer={setActiveLayer}
        signalsPanelVisible={signalsPanelVisible}
        onToggleSignalsPanel={() => setSignalsPanelVisible((v) => !v)}
        alertZones={alertZones}
        onSelectZone={handleSelectZone}
      />
      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">LONDON / LIVE SYSTEM</p>
            <h1>City pulse</h1>
          </div>
          <div className="summary">
            <small>METRONOME</small>
            <strong>{globalScore ?? "–"}</strong>
            {globalState && <span style={{ color: scoreStateColor(globalState) }}>{globalState}</span>}
          </div>
        </header>

        <main className="stage">
          <div className="mapContainer">
            <MapView
              zones={zones}
              selectedZoneId={selectedZoneId}
              onSelectZone={handleSelectZone}
              activeLayer={activeLayer}
            />
          </div>

          <Toast message={toastMessage} visible={toastVisible} />
          {signalsPanelVisible && <SignalsPanel zones={zones} />}
          <Legend title={layerLabel(activeLayer)} />
          <ZoneCard zone={selectedZone} delta={delta} />
          <Timestamp lastUpdated={lastUpdated} />
        </main>
      </section>
    </div>
  );
}
