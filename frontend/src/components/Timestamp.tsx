import { useEffect, useState } from "react";

interface TimestampProps {
  lastUpdated: Date | null;
}

export default function Timestamp({ lastUpdated }: TimestampProps) {
  const [, forceTick] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => forceTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  if (!lastUpdated) {
    return <div className="timestamp">CONNECTING…</div>;
  }

  const seconds = Math.max(0, Math.round((Date.now() - lastUpdated.getTime()) / 1000));
  const label = seconds < 60 ? `${seconds} SEC AGO` : `${Math.round(seconds / 60)} MIN AGO`;

  return <div className="timestamp">UPDATED {label}</div>;
}
