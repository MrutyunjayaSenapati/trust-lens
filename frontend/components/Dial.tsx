import type { Verdict } from "@/lib/types";
import { VERDICT_COLOR } from "@/lib/verdict";

/** Score dial: 24 spokes (a nod to the chakra) that fill in as the score rises. */
export default function Dial({ score, verdict, label }: { score: number; verdict: Verdict; label: string }) {
  const { fg } = VERDICT_COLOR[verdict];
  const N = 24;
  const lit = Math.round((score / 100) * N);
  return (
    <svg viewBox="0 0 200 200" className="w-full max-w-[210px]" role="img" aria-label={`${label} ${score} / 100`}>
      <circle cx="100" cy="100" r="96" fill="#FFFDF8" stroke="#E4D8BF" />
      <circle cx="100" cy="100" r="60" fill="none" stroke="#E4D8BF" strokeDasharray="2 4" />
      {Array.from({ length: N }, (_, i) => {
        const a = (i / N) * Math.PI * 2 - Math.PI / 2;
        const on = i < lit;
        return (
          <line key={i} x1={100 + Math.cos(a) * 66} y1={100 + Math.sin(a) * 66} x2={100 + Math.cos(a) * 90} y2={100 + Math.sin(a) * 90}
                stroke={on ? fg : "#E4D8BF"} strokeWidth={on ? 5 : 3.5} strokeLinecap="round"
                className={on ? "tick" : undefined} style={on ? { animationDelay: `${i * 35}ms` } : undefined} />
        );
      })}
      <text x="100" y="108" textAnchor="middle" fontSize="54" fontWeight="600" fill="#1A1633" style={{ fontFamily: "var(--font-display, 'Fraunces Variable', Georgia, serif)" }}>{score}</text>
      <text x="100" y="130" textAnchor="middle" fontSize="10" letterSpacing="2.4" fill="#8A85A3" className="font-mono">/ 100</text>
    </svg>
  );
}
