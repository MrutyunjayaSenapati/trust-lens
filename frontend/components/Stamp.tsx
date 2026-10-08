import type { Verdict } from "@/lib/types";
import { VERDICT_COLOR } from "@/lib/verdict";

/** Rubber-stamp verdict, like an office "RECEIVED" seal. Ink-bleed comes from the #rough SVG filter in layout. */
export default function Stamp({ verdict, text, sub }: { verdict: Verdict; text: string; sub?: string }) {
  const { fg } = VERDICT_COLOR[verdict];
  return (
    <div className="stampdown inline-block select-none" style={{ color: fg }} aria-hidden>
      <div className="rough rounded-xl border-[3px] px-4 py-2 text-center" style={{ borderColor: fg, boxShadow: `inset 0 0 0 2px #FFFDF8, inset 0 0 0 4px ${fg}` }}>
        <p className="font-display text-[26px] font-bold uppercase leading-none tracking-wider sm:text-[30px]">{text}</p>
        {sub && <p className="mt-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.3em]">{sub}</p>}
      </div>
    </div>
  );
}
