import { useEffect, useState } from "react";

import MapView from "./components/MapView";
import ScoreLegend from "./components/ScoreLegend";
import { getHealth, getZones } from "./lib/api";
import type { ZoneScore } from "./types";

export default function App() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "ok" | "error">("checking");
  const [zones, setZones] = useState<ZoneScore[]>([]);

  useEffect(() => {
    getHealth()
      .then(() => setBackendStatus("ok"))
      .catch(() => setBackendStatus("error"));

    getZones()
      .then(setZones)
      .catch(() => setZones([]));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          padding: "0.75rem 1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #333",
          background: "#111",
          color: "#eee",
        }}
      >
        <strong>Metronome</strong>
        <span>
          backend: {backendStatus} · zones: {zones.length}
        </span>
      </header>
      <main style={{ flex: 1, position: "relative" }}>
        <MapView zones={zones} />
        <ScoreLegend />
      </main>
    </div>
  );
}
