import { useState } from "react";

import { LAYER_OPTIONS, type LayerKey } from "../lib/layers";
import { scoreState } from "../lib/scoreState";
import type { ZoneScore } from "../types";

type PopoverKey = "layers" | "alerts" | null;

interface RailProps {
  live: boolean;
  activeLayer: LayerKey;
  onChangeLayer: (layer: LayerKey) => void;
  signalsPanelVisible: boolean;
  onToggleSignalsPanel: () => void;
  alertZones: ZoneScore[];
  onSelectZone: (id: string) => void;
}

export default function Rail({
  live,
  activeLayer,
  onChangeLayer,
  signalsPanelVisible,
  onToggleSignalsPanel,
  alertZones,
  onSelectZone,
}: RailProps) {
  const [openPopover, setOpenPopover] = useState<PopoverKey>(null);

  const togglePopover = (key: Exclude<PopoverKey, null>) => {
    setOpenPopover((current) => (current === key ? null : key));
  };

  return (
    <aside className="rail" onMouseLeave={() => setOpenPopover(null)}>
      <div className="logo">M</div>
      <nav className="nav">
        <button className="icon active" type="button" title="Map">
          ◉
        </button>

        <div>
          <button
            className={`icon${openPopover === "layers" ? " active" : ""}`}
            type="button"
            title="Layers"
            onClick={() => togglePopover("layers")}
          >
            ◇
          </button>
          {openPopover === "layers" && (
            <div className="rail-popover">
              {LAYER_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  className={`rail-popover-item${activeLayer === option.key ? " active" : ""}`}
                  onClick={() => {
                    onChangeLayer(option.key);
                    setOpenPopover(null);
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          className={`icon${signalsPanelVisible ? " active" : ""}`}
          type="button"
          title={signalsPanelVisible ? "Hide city signals" : "Show city signals"}
          onClick={onToggleSignalsPanel}
        >
          ≋
        </button>

        <div>
          <button
            className={`icon${openPopover === "alerts" ? " active" : ""}`}
            type="button"
            title="Alerts"
            onClick={() => togglePopover("alerts")}
          >
            ⌁
            {alertZones.length > 0 && <span className="rail-badge" />}
          </button>
          {openPopover === "alerts" && (
            <div className="rail-popover">
              {alertZones.length === 0 ? (
                <div className="rail-popover-empty">No active alerts</div>
              ) : (
                alertZones.map((zone) => (
                  <button
                    key={zone.id}
                    type="button"
                    className="rail-popover-item"
                    onClick={() => {
                      onSelectZone(zone.id);
                      setOpenPopover(null);
                    }}
                  >
                    {zone.name} · {scoreState(zone.score)}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </nav>
      <div
        className="live"
        title={live ? "Live" : "Connecting…"}
        style={live ? undefined : { background: "#444", boxShadow: "none" }}
      />
    </aside>
  );
}
