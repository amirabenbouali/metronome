import { useEffect, useState } from "react";

import { getZoneEvents } from "../lib/api";
import { scoreState, scoreStateColor } from "../lib/scoreState";
import type { ZoneScore } from "../types";

interface ZoneCardProps {
  zone: ZoneScore | null;
  delta: number | null;
}

function formatDelta(delta: number | null): string {
  if (delta === null) return "Watching for the next update…";
  if (delta === 0) return "No change since last update";
  const arrow = delta > 0 ? "↑" : "↓";
  return `${arrow} ${delta > 0 ? "+" : ""}${delta} since last update`;
}

export default function ZoneCard({ zone, delta }: ZoneCardProps) {
  const [eventsExpanded, setEventsExpanded] = useState(false);
  const [fullEvents, setFullEvents] = useState<string[] | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(false);

  // Collapse and drop any fetched list whenever the focused zone changes,
  // so it doesn't linger showing stale events for whatever was focused
  // before, and so switching back later re-fetches fresh data.
  useEffect(() => {
    setEventsExpanded(false);
    setFullEvents(null);
  }, [zone?.id]);

  if (!zone) {
    return (
      <section className="panel zonecard">
        <p className="eyebrow">FOCUSED ZONE</p>
        <h2>Select a zone</h2>
        <div className="driver">Click any zone on the map, or search above, to see its live breakdown.</div>
      </section>
    );
  }

  const handleToggleEvents = async () => {
    if (eventsExpanded) {
      setEventsExpanded(false);
      return;
    }
    setEventsExpanded(true);
    if (fullEvents !== null) return; // already fetched for this zone

    setLoadingEvents(true);
    try {
      const events = await getZoneEvents(zone.id);
      setFullEvents(events);
    } catch {
      setFullEvents([]); // fail quietly rather than breaking the card
    } finally {
      setLoadingEvents(false);
    }
  };

  const state = scoreState(zone.score);
  const rows: Array<{ label: string; text: string }> = [
    { label: "Traffic", text: zone.details.traffic },
    { label: "Transit", text: zone.details.transit },
    { label: "Weather", text: zone.details.weather },
  ];

  return (
    <section className="panel zonecard">
      <p className="eyebrow">FOCUSED ZONE</p>
      <h2>{zone.name}</h2>
      <div className="scoreline">
        <strong>{Math.round(zone.score)}</strong>
        <span style={{ color: scoreStateColor(state) }}>{state}</span>
      </div>
      <div className="delta">{formatDelta(delta)}</div>
      <div className="detailgrid">
        {rows.map((row) => (
          <div className="detailrow" key={row.label}>
            <span>{row.label.toUpperCase()}</span>
            <p>{row.text}</p>
          </div>
        ))}
        <div className="detailrow">
          <span>EVENTS</span>
          <p>{zone.details.events}</p>
          {zone.event_count > 0 && (
            <button type="button" className="events-toggle" onClick={handleToggleEvents}>
              {eventsExpanded ? "Hide list" : `See all ${zone.event_count}`}
            </button>
          )}
          {eventsExpanded &&
            (loadingEvents ? (
              <p className="events-loading">Loading…</p>
            ) : (
              <ul className="events-list">
                {(fullEvents ?? zone.events).map((event, i) => (
                  <li key={i}>{event}</li>
                ))}
              </ul>
            ))}
        </div>
      </div>
    </section>
  );
}
