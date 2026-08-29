export type ScoreState = "CALM" | "STEADY" | "ELEVATED" | "BUSY" | "INTENSE";

// Bands roughly follow the reference design's sample data points
// (South Bank 42=CALM, Paddington 51=STEADY, Camden 64=ELEVATED,
// Canary Wharf 73=BUSY, Shoreditch 84=INTENSE).
export const SCORE_BANDS: Array<{ min: number; max: number; state: ScoreState }> = [
  { min: 0, max: 44, state: "CALM" },
  { min: 45, max: 59, state: "STEADY" },
  { min: 60, max: 69, state: "ELEVATED" },
  { min: 70, max: 79, state: "BUSY" },
  { min: 80, max: 100, state: "INTENSE" },
];

export function scoreState(score: number): ScoreState {
  return SCORE_BANDS.find((band) => score <= band.max)!.state;
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
