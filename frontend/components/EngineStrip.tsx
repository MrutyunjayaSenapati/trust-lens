import { ENGINE_LABEL } from "@/lib/types";

const ORDER = ["google", "google_news", "google_maps", "google_jobs", "google_shopping", "google_lens"] as const;

const ICON: Record<string, JSX.Element> = {
  google: <><circle cx="10.5" cy="10.5" r="5.5" /><path d="M15 15l5 5" /></>,
  google_news: <><rect x="4" y="5" width="16" height="14" rx="2" /><path d="M8 9h8M8 12h8M8 15h5" /></>,
  google_maps: <><path d="M12 21s-6.5-5.6-6.5-10.5a6.5 6.5 0 0113 0C18.5 15.4 12 21 12 21z" /><circle cx="12" cy="10.5" r="2.3" /></>,
  google_jobs: <><rect x="4" y="8" width="16" height="11" rx="2" /><path d="M9 8V6.5A1.5 1.5 0 0110.5 5h3A1.5 1.5 0 0115 6.5V8M4 13h16" /></>,
  google_shopping: <><path d="M5 8h14l-1.2 11H6.2L5 8z" /><path d="M9 8V7a3 3 0 016 0v1" /></>,
  google_lens: <><circle cx="12" cy="12" r="3.2" /><path d="M4 8V5.5A1.5 1.5 0 015.5 4H8M16 4h2.5A1.5 1.5 0 0120 5.5V8M20 16v2.5a1.5 1.5 0 01-1.5 1.5H16M8 20H5.5A1.5 1.5 0 014 18.5V16" /></>,
};

export function EngineIcon({ id, className = "h-4 w-4" }: { id: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {ICON[id] || ICON.google}
    </svg>
  );
}

/** Six engines; each lights up as it is planned, pulses while searching and ticks when it returned evidence. */
export default function EngineStrip({ planned, done, running }: { planned: string[]; done: string[]; running: boolean }) {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="SerpApi engines">
      {ORDER.map((id) => {
        const isPlanned = planned.includes(id);
        const isDone = done.includes(id);
        const searching = running && isPlanned && !isDone;
        return (
          <li key={id}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
                isDone ? "border-safe/40 bg-safe-wash text-safe" : isPlanned ? "border-saffron/50 bg-saffron-wash text-saffron-deep" : "border-line bg-paper-card text-ink-faint"
              } ${searching ? "searching" : ""}`}>
            <EngineIcon id={id} />
            <span className="font-medium">{ENGINE_LABEL[id].replace("Google ", "")}</span>
            {isDone && <span aria-hidden>✓</span>}
          </li>
        );
      })}
    </ul>
  );
}
