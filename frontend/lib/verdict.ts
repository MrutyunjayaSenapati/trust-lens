import type { Verdict } from "./types";

export const VERDICT_COLOR: Record<Verdict, { fg: string; wash: string }> = {
  likely_genuine: { fg: "#0F7B3E", wash: "#DDF3E4" },
  verify: { fg: "#B7791F", wash: "#FDF1CF" },
  suspicious: { fg: "#D9570F", wash: "#FDE6D8" },
  likely_scam: { fg: "#B3261E", wash: "#FADDD9" },
};

export const FLAGGED: Verdict[] = ["suspicious", "likely_scam"];
