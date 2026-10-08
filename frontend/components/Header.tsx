"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Brand from "./Brand";
import { useLang } from "@/lib/i18n";

export default function Header() {
  const { lang, setLang, t } = useLang();
  const [canInstall, setCanInstall] = useState(false);

  useEffect(() => {
    const sync = () => setCanInstall(!!(window as any).__tlInstall);
    sync();
    window.addEventListener("tl-installable", sync);
    window.addEventListener("tl-installed", sync);
    return () => { window.removeEventListener("tl-installable", sync); window.removeEventListener("tl-installed", sync); };
  }, []);

  async function install() {
    const ev = (window as any).__tlInstall;
    if (!ev) return;
    ev.prompt();
    await ev.userChoice.catch(() => {});
    (window as any).__tlInstall = null;
    setCanInstall(false);
  }

  return (
    <header>
      <div className="tiranga" />
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <Link href="/" aria-label="TrustLens home"><Brand /></Link>
        <nav className="flex items-center gap-2 text-sm">
          <Link href="/benchmark" className="hidden rounded-full px-3 py-1.5 text-ink-soft hover:bg-paper-2 sm:block">{t.navBenchmark}</Link>
          {canInstall && (
            <button onClick={install} className="hidden rounded-full border border-line-strong px-3 py-1.5 text-ink hover:bg-paper-2 sm:block">{t.install}</button>
          )}
          <div className="flex overflow-hidden rounded-full border border-line-strong bg-paper-card" role="group" aria-label="Language">
            {(["en", "hi"] as const).map((l) => (
              <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l}
                className={`px-3 py-1.5 text-sm font-medium transition ${lang === l ? "bg-ink text-paper" : "text-ink-soft hover:bg-paper-2"}`}>
                {l === "en" ? "EN" : "हिन्दी"}
              </button>
            ))}
          </div>
        </nav>
      </div>
      <div className="pallu" aria-hidden />
    </header>
  );
}
