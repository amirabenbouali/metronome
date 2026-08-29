import { useMemo, useState } from "react";

import type { ZoneScore } from "../types";

interface SearchProps {
  zones: ZoneScore[];
  onFocusZone: (id: string) => void;
}

export default function Search({ zones, onFocusZone }: SearchProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return zones
      .filter((zone) => zone.name.toLowerCase().includes(q))
      .sort((a, b) => a.name.localeCompare(b.name))
      .slice(0, 8);
  }, [zones, query]);

  const handleSelect = (zone: ZoneScore) => {
    onFocusZone(zone.id);
    setQuery("");
    setOpen(false);
  };

  return (
    <div className="search">
      <input
        type="text"
        className="search-input"
        placeholder="Search a borough…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setQuery("");
            setOpen(false);
            e.currentTarget.blur();
          } else if (e.key === "Enter" && results.length > 0) {
            handleSelect(results[0]);
          }
        }}
      />
      {open && query.trim() !== "" && (
        <div className="search-results">
          {results.length === 0 ? (
            <div className="search-empty">No boroughs match "{query}"</div>
          ) : (
            results.map((zone) => (
              <button
                key={zone.id}
                type="button"
                className="search-result"
                // onMouseDown (not onClick) fires before the input's onBlur,
                // so the click actually registers instead of the dropdown
                // closing out from under it first.
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(zone);
                }}
              >
                {zone.name}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
