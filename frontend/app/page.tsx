"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Dial from "@/components/Dial";
import EngineStrip, { EngineIcon } from "@/components/EngineStrip";
import Footer from "@/components/Footer";
import Graph from "@/components/Graph";
import Header from "@/components/Header";
import Stamp from "@/components/Stamp";
import { useLang } from "@/lib/i18n";
import { renderShareCard } from "@/lib/shareCard";
import { API, investigate } from "@/lib/stream";
import { Contradiction, ENGINE_LABEL, Entities, Evidence, Example, Result } from "@/lib/types";
import { VERDICT_COLOR } from "@/lib/verdict";

type Shot = { name: string; b64: string; mime: string; preview: string };

function WeightChip({ w }: { w: number }) {
  if (!w) return null;
  return (
    <span className={`rounded-md px-1.5 py-0.5 font-mono text-[11px] font-medium ${w > 0 ? "bg-safe-wash text-safe" : "bg-scam-wash text-scam"}`}>
      {w > 0 ? `+${w}` : w}
    </span>
  );
}

function EvidenceCard({ e }: { e: Evidence }) {
  const rail = e.signal === "positive" ? "bg-safe" : e.signal === "negative" ? "bg-scam" : "bg-line-strong";
  return (
    <li className="rise flex gap-3 rounded-xl border border-line bg-paper-card p-3.5 shadow-card">
      <span className={`w-1 shrink-0 rounded-full ${rail}`} aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-medium uppercase tracking-widest text-chakra">
            <EngineIcon id={e.engine} className="h-3.5 w-3.5" />
            {ENGINE_LABEL[e.engine] || e.engine}
          </span>
          <WeightChip w={e.weight} />
        </div>
        <p className="mt-1 font-semibold text-ink">{e.title}</p>
        <p className="text-sm leading-relaxed text-ink-soft">{e.detail}</p>
        {e.sources.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {e.sources.map((s, i) => (
              <li key={i} className="truncate text-xs">
                <a href={s.url} target="_blank" rel="noreferrer noopener" className="text-chakra underline decoration-chakra/30 underline-offset-2 hover:decoration-chakra">
                  {s.title || s.url}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}

function ContradictionCard({ c }: { c: Contradiction }) {
  return (
    <li className="rise rounded-xl border border-scam/40 bg-scam-wash p-3.5">
      <div className="flex items-center gap-2">
        <span aria-hidden className="grid h-5 w-5 place-items-center rounded-full bg-scam text-[11px] font-bold text-paper-card">!</span>
        <WeightChip w={c.weight} />
      </div>
      <p className="mt-1.5 font-semibold text-ink">{c.title}</p>
      <p className="text-sm leading-relaxed text-ink-soft">{c.detail}</p>
    </li>
  );
}

function Spinner() {
  return <span className="spin inline-block h-3 w-3 rounded-full border-2 border-saffron border-t-transparent" aria-hidden />;
}

export default function Home() {
  const { lang, t } = useLang();
  const [text, setText] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [shot, setShot] = useState<Shot | null>(null);
  const [examples, setExamples] = useState<Example[]>([]);
  const [running, setRunning] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [planned, setPlanned] = useState<string[]>([]);
  const [entities, setEntities] = useState<Entities | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [contras, setContras] = useState<Contradiction[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [dragging, setDragging] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const out = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API}/api/examples`).then((r) => r.json()).then(setExamples).catch(() => {});
  }, []);

  // PWA share target: other apps (WhatsApp, SMS, browser) open us as /?title=&text=&url=
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const shared = [q.get("title"), q.get("text"), q.get("url")].filter(Boolean).join("\n").trim();
    if (shared) {
      setText(shared);
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  function onFile(f: File | undefined | null) {
    if (!f || !f.type.startsWith("image/")) return;
    const rd = new FileReader();
    rd.onload = () => {
      const s = String(rd.result);
      setShot({ name: f.name || "screenshot", b64: s.split(",")[1] || "", mime: f.type || "image/png", preview: s });
    };
    rd.readAsDataURL(f);
  }

  async function run() {
    if (running) return abort.current?.abort();
    setRunning(true); setError(null); setResult(null); setLog([]); setPlanned([]); setEntities(null); setEvidence([]); setContras([]);
    abort.current = new AbortController();
    setTimeout(() => out.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    try {
      for await (const ev of investigate(
        { text, image_base64: shot?.b64, image_mime: shot?.mime, image_url: imageUrl.trim() || undefined },
        abort.current.signal
      )) {
        if (ev.type === "stage") {
          setLog((l) => [...l, ev.message]);
          if (ev.engines) setPlanned(ev.engines);
        } else if (ev.type === "entities") setEntities(ev.entities);
        else if (ev.type === "evidence") setEvidence((l) => [...l, ev.item]);
        else if (ev.type === "contradiction") setContras((l) => [...l, ev.item]);
        else if (ev.type === "result") {
          // the reasoner can re-weigh streamed evidence once every engine has answered, so the result is authoritative
          setEvidence(ev.result.evidence);
          setContras(ev.result.contradictions);
          setResult(ev.result);
        }
        else if (ev.type === "error") setError(ev.message);
      }
    } catch (e: any) {
      if (e?.name !== "AbortError") setError(`${t.apiDown} (${API})`);
    } finally {
      setRunning(false);
    }
  }

  const hi = lang === "hi";
  const verdictT = result ? t.verdicts[result.verdict] : null;
  const color = result ? VERDICT_COLOR[result.verdict] : null;
  const explanation = result ? (hi && result.explanation_hi ? result.explanation_hi : result.explanation) : "";
  const steps = result ? (hi && result.next_steps_hi?.length ? result.next_steps_hi : result.next_steps) : [];
  const warning = result ? (hi ? result.warning_hi : result.warning_en) : "";
  const started = running || !!result || !!error || evidence.length > 0;

  const doneEngines = useMemo(
    () => (result ? planned : Array.from(new Set(evidence.map((e) => e.engine)))),
    [result, planned, evidence]
  );

  const ledger = useMemo(() => {
    if (!result) return [];
    const rows = [
      ...result.evidence.map((e) => ({ id: e.id, title: e.title, w: e.weight })),
      ...result.contradictions.map((c) => ({ id: c.id, title: c.title, w: c.weight })),
    ].filter((r) => r.w !== 0);
    return rows.sort((a, b) => a.w - b.w);
  }, [result]);

  async function card(): Promise<Blob | null> {
    if (!result || !verdictT) return null;
    return renderShareCard(result, lang, verdictT.stamp, warning, t.shareHeading, t.shareFoot);
  }
  function download(blob: Blob) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "trustlens-check.png";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  async function onDownload() {
    setSharing(true);
    try { const b = await card(); if (b) download(b); } finally { setSharing(false); }
  }
  async function onNativeShare() {
    setSharing(true);
    try {
      const b = await card();
      if (!b) return;
      const file = new File([b], "trustlens-check.png", { type: "image/png" });
      const nav: any = navigator;
      if (nav.canShare?.({ files: [file] })) await nav.share({ files: [file], text: warning });
      else if (nav.share) await nav.share({ text: `${warning}\n\n${t.shareFoot}`, url: window.location.origin });
      else download(b);
    } catch (e: any) {
      if (e?.name !== "AbortError") { const b = await card(); if (b) download(b); }
    } finally { setSharing(false); }
  }
  function onWhatsApp() {
    const msg = `${warning}\n\n${t.shareFoot}\n${window.location.origin}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, "_blank", "noopener");
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-4 pb-8 sm:px-6">
        {/* hero */}
        <section className="pb-6 pt-10 sm:pt-14">
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.28em] text-saffron-deep">{t.tagline}</p>
          <h1 className="mt-3 max-w-3xl font-display text-[40px] font-semibold leading-[1.08] tracking-tight text-ink sm:text-[64px]">
            {t.heroA}{" "}
            <span className="relative inline-block italic text-saffron">
              {t.heroB}
              <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 200 12" preserveAspectRatio="none" aria-hidden>
                <path d="M2 8 C 40 2, 80 12, 120 6 S 180 4, 198 7" fill="none" stroke="#138808" strokeWidth="3.5" strokeLinecap="round" />
              </svg>
            </span>
            {t.heroC}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink-soft">{t.heroSub}</p>
        </section>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,430px)_1fr]">
          {/* input */}
          <section className="lg:sticky lg:top-6 lg:self-start">
            <div className="postcard p-6 shadow-lift">
              <div className="relative z-10">
                <label htmlFor="msg" className="font-display text-2xl font-semibold">{t.pasteLabel}</label>
                <p className="mt-1 text-sm text-ink-soft">{t.pasteHelp}</p>
                <textarea id="msg" value={text} onChange={(e) => setText(e.target.value)} rows={6}
                  onPaste={(e) => { const f = Array.from(e.clipboardData.files).find((x) => x.type.startsWith("image/")); if (f) { e.preventDefault(); onFile(f); } }}
                  placeholder={t.pastePlaceholder}
                  className="mt-3 w-full resize-y rounded-xl border border-line-strong bg-paper p-3 text-[16px] leading-relaxed text-ink placeholder:text-ink-faint focus:border-saffron focus:outline-none focus:ring-2 focus:ring-saffron/30" />

                {examples.length > 0 && (
                  <div className="mt-3">
                    <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">{t.examples}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {examples.map((ex) => (
                        <button key={ex.id} onClick={() => setText(ex.text)}
                          className="rounded-full border border-line-strong bg-paper-card px-3 py-1 text-[13px] text-ink-soft transition hover:border-saffron hover:bg-saffron-wash hover:text-saffron-deep">
                          {ex.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-4">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">{t.screenshot}</p>
                  {shot ? (
                    <div className="mt-1.5 flex items-center gap-3 rounded-xl border border-line-strong bg-paper p-2">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={shot.preview} alt="" className="h-14 w-14 rounded-lg object-cover" />
                      <span className="min-w-0 flex-1 truncate text-sm text-ink-soft">{shot.name}</span>
                      <button onClick={() => setShot(null)} className="rounded-full px-3 py-1 text-sm text-scam hover:bg-scam-wash">{t.screenshotChange}</button>
                    </div>
                  ) : (
                    <label onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
                      onDrop={(e) => { e.preventDefault(); setDragging(false); onFile(e.dataTransfer.files?.[0]); }}
                      className={`mt-1.5 flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed p-3 text-sm transition ${dragging ? "border-saffron bg-saffron-wash" : "border-line-strong bg-paper hover:border-saffron/60"}`}>
                      <svg viewBox="0 0 24 24" className="h-6 w-6 shrink-0 text-saffron" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="9" cy="10" r="1.6" /><path d="M21 16l-5-5-8 8" />
                      </svg>
                      <span className="text-ink-soft">{t.screenshotHelp}</span>
                      <input type="file" accept="image/*" className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
                    </label>
                  )}
                </div>

                <details className="mt-3 text-sm">
                  <summary className="cursor-pointer text-ink-soft hover:text-ink">{t.imageUrl}</summary>
                  <input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://…/photo.jpg"
                    className="mt-2 w-full rounded-lg border border-line-strong bg-paper px-3 py-2 text-sm focus:border-saffron focus:outline-none" />
                </details>

                <button onClick={run} disabled={!running && !text.trim() && !shot}
                  className="mt-5 w-full rounded-xl bg-saffron px-4 py-3.5 text-[17px] font-semibold text-paper-card shadow-card transition hover:bg-saffron-deep active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40">
                  {running ? t.stop : t.investigate}
                </button>
                <p className="mt-2.5 text-xs text-ink-faint">{t.privacy}</p>
              </div>
            </div>
          </section>

          {/* results */}
          <section ref={out} className="min-w-0 scroll-mt-6" aria-live="polite">
            {!started && (
              <div className="rounded-2xl border-2 border-dashed border-line-strong p-10 text-center">
                <div className="mx-auto mb-4 w-fit"><EngineStrip planned={[]} done={[]} running={false} /></div>
                <p className="font-display text-2xl text-ink">{t.emptyTitle}</p>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-soft">{t.emptyBody}</p>
              </div>
            )}

            {started && (
              <div className="space-y-6">
                <EngineStrip planned={planned} done={doneEngines} running={running} />
                {error && <p role="alert" className="rounded-xl border border-scam/50 bg-scam-wash p-3 text-sm text-scam">{error}</p>}

                {log.length > 0 && (
                  <ol className="space-y-1 font-mono text-xs text-ink-soft">
                    {log.map((l, i) => (
                      <li key={i} className="rise flex items-start gap-2">
                        {running && i === log.length - 1 ? <span className="mt-0.5"><Spinner /></span> : <span className="text-tiranga">✓</span>}
                        <span>{l}</span>
                      </li>
                    ))}
                  </ol>
                )}

                {entities && (
                  <div className="rise rounded-xl border border-line bg-paper-card p-3.5 text-sm">
                    <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">{t.extracted}</p>
                    <p className="mt-1 text-ink-soft">
                      <b className="text-ink">{entities.company || entities.product || t.unknownCompany}</b>
                      {entities.role ? ` · ${entities.role}` : ""}{entities.city ? ` · ${entities.city}` : ""}
                      {entities.contact_email ? ` · ${entities.contact_email}` : ""}
                    </p>
                  </div>
                )}

                {result?.source_note && <p className="rounded-lg bg-turmeric-wash px-3 py-2 text-sm text-ink-soft">🔗 {result.source_note}</p>}

                {result && verdictT && color && (
                  <article className="postcard rise p-5 shadow-lift sm:p-6" style={{ borderColor: color.fg + "55" }}>
                    <div className="relative z-10">
                      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
                        <Dial score={result.score} verdict={result.verdict} label={t.scoreLabel} />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-ink-faint">{t.verdictWord} · {t.confidence[result.confidence]}</p>
                              <h2 className="mt-1 font-display text-4xl font-semibold leading-tight" style={{ color: color.fg }}>{verdictT.label}</h2>
                            </div>
                            <Stamp verdict={result.verdict} text={verdictT.stamp} sub="TrustLens" />
                          </div>
                          <p className="mt-3 leading-relaxed text-ink">{explanation}</p>
                          <p className="mt-2 text-sm text-ink-soft">{verdictT.blurb}</p>
                        </div>
                      </div>
                      <div className="mt-5 rounded-xl bg-paper p-4">
                        <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">{t.whatToDo}</p>
                        <ol className="mt-2 space-y-1.5 text-[15px] text-ink">
                          {steps.map((s, i) => (
                            <li key={i} className="flex gap-2.5">
                              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-ink text-[11px] font-medium text-paper">{i + 1}</span>
                              <span>{s}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                      <p className="mt-3 text-xs text-ink-faint">{t.liveCalls(result.live_calls, result.cache_hits)}</p>
                    </div>
                  </article>
                )}

                {contras.length > 0 && (
                  <div>
                    <h3 className="font-display text-2xl font-semibold">{t.disagree}</h3>
                    <ul className="mt-3 space-y-2.5">{contras.map((c) => (<ContradictionCard key={c.id} c={c} />))}</ul>
                  </div>
                )}

                {evidence.length > 0 && (
                  <div>
                    <h3 className="font-display text-2xl font-semibold">{t.evidence}</h3>
                    <ul className="mt-3 space-y-2.5">{evidence.map((e) => (<EvidenceCard key={e.id} e={e} />))}</ul>
                  </div>
                )}

                {result && (
                  <div className="rounded-2xl border border-line bg-paper-card p-5 shadow-card">
                    <h3 className="font-display text-2xl font-semibold">{t.ledger}</h3>
                    <p className="mt-1 text-xs text-ink-faint">{t.ledgerNote}</p>
                    <ul className="mt-3 divide-y divide-line text-sm">
                      <li className="flex justify-between py-1.5"><span className="text-ink-soft">{t.ledgerBase}</span><span className="font-mono">50</span></li>
                      {ledger.map((r) => (
                        <li key={r.id} className="flex items-center justify-between gap-3 py-1.5">
                          <span className="min-w-0 truncate text-ink-soft">{r.title}</span><WeightChip w={r.w} />
                        </li>
                      ))}
                      <li className="flex justify-between pt-2 font-semibold"><span>{t.ledgerTotal}</span><span className="font-mono" style={{ color: color?.fg }}>{result.score}</span></li>
                    </ul>
                  </div>
                )}

                {result && (
                  <div>
                    <h3 className="font-display text-2xl font-semibold">{t.graph}</h3>
                    <p className="text-xs text-ink-faint">{t.graphHint}</p>
                    <div className="mt-2 rounded-2xl border border-line bg-paper-card p-2 shadow-card">
                      <Graph nodes={result.graph_nodes} edges={result.graph_edges} />
                    </div>
                  </div>
                )}

                {result && (
                  <div className="postcard p-5 shadow-card">
                    <div className="relative z-10">
                      <h3 className="font-display text-2xl font-semibold">{t.warnFamily}</h3>
                      <p className="mt-3 whitespace-pre-wrap rounded-xl bg-paper p-3.5 text-[15px] leading-relaxed text-ink">{warning}</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button onClick={onWhatsApp} className="inline-flex items-center gap-2 rounded-xl bg-[#1FA855] px-4 py-2.5 font-semibold text-white shadow-card transition hover:brightness-95">
                          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.2 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7a11 11 0 01-4.6-4c-.4-.5-1.1-1.5-1.1-2.8s.7-1.9 1-2.2c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.9 2.1c.1.2.1.4 0 .5l-.3.5-.4.4c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.1 1 2 1.3 2.3 1.4.3.1.4.1.6-.1l.8-1c.2-.2.4-.2.6-.1l2 .9c.2.1.4.2.5.3.1.2.1.8-.1 1.4z" /></svg>
                          {t.whatsapp}
                        </button>
                        <button onClick={onDownload} disabled={sharing} className="rounded-xl border border-line-strong bg-paper-card px-4 py-2.5 font-medium text-ink hover:bg-paper-2 disabled:opacity-50">{t.downloadCard}</button>
                        <button onClick={onNativeShare} disabled={sharing} className="rounded-xl border border-line-strong bg-paper-card px-4 py-2.5 font-medium text-ink hover:bg-paper-2 disabled:opacity-50">{t.share}</button>
                        <button onClick={async () => { await navigator.clipboard.writeText(warning); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
                          className="rounded-xl border border-line-strong bg-paper-card px-4 py-2.5 font-medium text-ink hover:bg-paper-2">{copied ? t.copied : t.copy}</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
