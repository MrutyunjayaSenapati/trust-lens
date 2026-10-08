export function LensMark({ size = 36 }: { size?: number }) {
  const spokes = Array.from({ length: 24 }, (_, i) => {
    const a = (i / 24) * Math.PI * 2;
    return (
      <line key={i} x1={50 + Math.cos(a) * 17} y1={50 + Math.sin(a) * 17} x2={50 + Math.cos(a) * 33} y2={50 + Math.sin(a) * 33}
            stroke="#E8761A" strokeWidth={i % 2 ? 1.3 : 2} strokeLinecap="round" />
    );
  });
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden>
      <circle cx="50" cy="50" r="40" fill="#FFFDF8" stroke="#1A1633" strokeWidth="7" />
      {spokes}
      <circle cx="50" cy="50" r="8.5" fill="#1F3A93" />
      <line x1="79" y1="79" x2="94" y2="94" stroke="#138808" strokeWidth="9" strokeLinecap="round" />
    </svg>
  );
}

export default function Brand({ size = 36 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LensMark size={size} />
      <span className="font-display text-[26px] font-semibold leading-none tracking-tight text-ink">
        Trust<span className="text-saffron">Lens</span>
      </span>
    </span>
  );
}
