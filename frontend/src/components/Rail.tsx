interface RailProps {
  live: boolean;
}

export default function Rail({ live }: RailProps) {
  return (
    <aside className="rail">
      <div className="logo">M</div>
      <nav className="nav">
        <button className="icon active" type="button" title="Map">
          ◉
        </button>
        <button className="icon" type="button" title="Layers (coming soon)" disabled>
          ◇
        </button>
        <button className="icon" type="button" title="Signals (coming soon)" disabled>
          ≋
        </button>
        <button className="icon" type="button" title="Alerts (coming soon)" disabled>
          ⌁
        </button>
      </nav>
      <div
        className="live"
        title={live ? "Live" : "Connecting…"}
        style={live ? undefined : { background: "#444", boxShadow: "none" }}
      />
    </aside>
  );
}
