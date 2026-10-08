"use client";
import { useLang } from "@/lib/i18n";

export default function Footer() {
  const { t } = useLang();
  return (
    <footer className="mt-20">
      <div className="pallu" aria-hidden />
      <div className="mx-auto max-w-6xl space-y-2 px-4 py-8 text-sm text-ink-soft sm:px-6">
        <p className="font-medium text-ink">{t.helpline}</p>
        <p>{t.footerA}</p>
        <p className="text-ink-faint">{t.footerB}</p>
      </div>
    </footer>
  );
}
