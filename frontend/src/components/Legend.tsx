interface LegendProps {
  title: string;
}

export default function Legend({ title }: LegendProps) {
  return (
    <div className="legend">
      <span className="legend-title">{title}</span>
      <span>CALM</span>
      <i />
      <span>INTENSE</span>
    </div>
  );
}
