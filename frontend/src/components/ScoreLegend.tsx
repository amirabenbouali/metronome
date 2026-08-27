const STOPS: Array<[number, string]> = [
  [0, "#2166ac"],
  [25, "#67a9cf"],
  [50, "#fee090"],
  [75, "#fc8d59"],
  [100, "#b2182b"],
];

export default function ScoreLegend() {
  const gradient = `linear-gradient(to right, ${STOPS.map(([, color]) => color).join(", ")})`;

  return (
    <div
      style={{
        position: "absolute",
        bottom: "1.5rem",
        left: "1rem",
        background: "rgba(17, 17, 17, 0.85)",
        color: "#eee",
        padding: "0.5rem 0.75rem",
        borderRadius: 6,
        fontSize: 12,
        width: 180,
      }}
    >
      <div style={{ marginBottom: 4 }}>Pulse score</div>
      <div style={{ height: 8, borderRadius: 4, background: gradient }} />
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
        <span>0</span>
        <span>100</span>
      </div>
    </div>
  );
}
