"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { useLang } from "@/lib/i18n";
import { API } from "@/lib/stream";
import type { Verdict } from "@/lib/types";
import { VERDICT_COLOR } from "@/lib/verdict";

interface Row { id: string; label: string; expected: "scam" | "genuine"; score?: number; verdict?: Verdict; confidence?: string; correct?: boolean; contradictions?: string[]; error?: boolean }
interface Bench {
  summary: null | { generated_at: string; total: number; correct: number; scams_caught: number; scams_total: number; genuine_cleared: number; genuine_total: number };
  rows: Row[];
}

function Big({ label, n, d }: { label: string; n: number; d: number }) {
  const pct = d ? Math.round((n / d) * 100) : 0;
  return (
    <div className="postcard p-5 text-center shadow-card">
      <div className="relative z-10">
        <p className="font-display text-5xl font-semibold text-ink">{n}<span className="text-2xl text-ink-faint">/{d}</span></p>
        <div className="mx-auto mt-3 h-2 w-full overflow-hidden rounded-full bg-paper-2"><div className="h-full rounded-full bg-tiranga" style={{ width: `${pct}%` }} /></div>
        <p className="mt-2 text-sm text-ink-soft">{label} · {pct}%</p>
      </div>
    </div>
  );
}

export default function Benchmark() {
  const { t } = useLang();
  const [data, setData] = useState<Bench | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/benchmark`).then((r) => r.json()).then(setData).catch(() => setFailed(true));
  }, []);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 pb-8 pt-10 sm:px-6">
        <Link href="/" className="text-sm text-chakra underline underline-offset-2">← {t.back}</Link>
        <h1 className="mt-4 font-display text-4xl font-semibold leading-tight sm:text-5xl">{t.bmTitle}</h1>
        <p className="mt-3 max-w-2xl text-lg text-ink-soft">{t.bmSub}</p>

        {failed && <p className="mt-8 rounded-xl border border-scam/40 bg-scam-wash p-3 text-sm text-scam">{t.apiDown}</p>}
        {data && !data.summary && <p className="mt-8 rounded-xl border border-dashed border-line-strong p-6 text-center text-ink-soft">{t.bmEmpty}</p>}

        {data?.summary && (
          <>
            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <Big label={t.bmCaught} n={data.summary.scams_caught} d={data.summary.scams_total} />
              <Big label={t.bmCleared} n={data.summary.genuine_cleared} d={data.summary.genuine_total} />
              <Big label={t.bmOverall} n={data.summary.correct} d={data.summary.total} />
            </div>

            <div className="mt-8 overflow-x-auto rounded-2xl border border-line bg-paper-card shadow-card">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-paper-2 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                  <tr><th className="p-3">{t.bmMsg}</th><th className="p-3">{t.bmExpected}</th><th className="p-3">{t.bmGot}</th><th className="p-3 text-right">{t.bmScore}</th><th className="p-3" /></tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.rows.map((r) => (
                    <tr key={r.id} className={r.correct === false ? "bg-scam-wash/50" : ""}>
                      <td className="p-3">
                        <p className="font-medium text-ink">{r.label}</p>
                        {r.contradictions && r.contradictions.length > 0 && <p className="mt-0.5 text-xs text-ink-faint">⚡ {r.contradictions.join(" · ")}</p>}
                      </td>
                      <td className="p-3">{r.expected === "scam" ? t.bmScam : t.bmGenuine}</td>
                      <td className="p-3">
                        {r.verdict ? <span className="rounded-md px-2 py-0.5 font-medium" style={{ color: VERDICT_COLOR[r.verdict].fg, background: VERDICT_COLOR[r.verdict].wash }}>{t.verdicts[r.verdict].label}</span> : "—"}
                      </td>
                      <td className="p-3 text-right font-mono">{r.score ?? "—"}</td>
                      <td className="p-3 text-right text-lg">{r.correct ? <span className="text-safe">✓</span> : <span className="text-scam">✗</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-sm text-ink-soft">{t.bmMethod}</p>
            <p className="mt-1 font-mono text-xs text-ink-faint">{data.summary.generated_at}</p>
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
