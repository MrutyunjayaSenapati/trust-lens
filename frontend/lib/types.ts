export type Signal = "positive" | "negative" | "neutral";
export type Verdict = "likely_genuine" | "verify" | "suspicious" | "likely_scam";

export interface Source { title: string; url: string }
export interface Evidence {
  id: string; engine: string; title: string; detail: string;
  signal: Signal; weight: number; sources: Source[];
}
export interface Contradiction {
  id: string; title: string; detail: string; evidence_ids: string[]; weight: number;
}
export interface Entities {
  kind: string; company?: string | null; role?: string | null; city?: string | null;
  contact_email?: string | null; phone?: string | null; website?: string | null;
  product?: string | null; summary: string;
}
export interface GraphNode { id: string; label: string; type: "subject" | "engine" | "evidence" | "contradiction"; signal?: Signal | null }
export interface GraphEdge { source: string; target: string; kind: string }
export interface Result {
  score: number; verdict: Verdict; confidence: "low" | "medium" | "high";
  entities: Entities; evidence: Evidence[]; contradictions: Contradiction[];
  explanation: string; next_steps: string[]; warning_en: string; warning_hi: string;
  explanation_hi?: string; next_steps_hi?: string[]; source_note?: string | null;
  graph_nodes: GraphNode[]; graph_edges: GraphEdge[]; engines_used: string[];
  live_calls: number; cache_hits: number;
}
export interface Example { id: string; label: string; text: string }

export type StreamEvent =
  | { type: "stage"; stage: string; message: string; engines?: string[] }
  | { type: "entities"; entities: Entities }
  | { type: "evidence"; item: Evidence }
  | { type: "contradiction"; item: Contradiction }
  | { type: "result"; result: Result }
  | { type: "error"; message: string };

export const ENGINE_LABEL: Record<string, string> = {
  google: "Google Search", google_news: "Google News", google_maps: "Google Maps",
  google_jobs: "Google Jobs", google_shopping: "Google Shopping", google_lens: "Google Lens",
  "text-analysis": "Text analysis",
};
