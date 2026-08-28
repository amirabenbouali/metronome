export type ScoreState = "CALM" | "STEADY" | "ELEVATED" | "BUSY" | "INTENSE";

// Bands roughly follow the reference design's sample data points
// (South Bank 42=CALM, Paddington 51=STEADY, Camden 64=ELEVATED,
// Canary Wharf 73=BUSY, Shoreditch 84=INTENSE).
const BANDS: Array<{ max: number; state: ScoreState }> = [
  { max: 44, state: "CALM" },
  { max: 59, state: "STEADY" },
  { max: 69, state: "ELEVATED" },
  { max: 79, state: "BUSY" },
  { max: Infinity, state: "INTENSE" },
];

export function scoreState(score: number): ScoreState {
  return BANDS.find((band) => score <= band.max)!.state;
}

const STATE_COLOR_VAR: Record<ScoreState, string> = {
  CALM: "var(--green)",
  STEADY: "var(--blue)",
  ELEVATED: "var(--amber)",
  BUSY: "var(--orange)",
  INTENSE: "var(--red)",
};

export function scoreStateColor(state: ScoreState): string {
  return STATE_COLOR_VAR[state];
}
