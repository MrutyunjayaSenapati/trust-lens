"use client";
import { useMemo, useState } from "react";
import { GraphEdge, GraphNode } from "@/lib/types";

const W = 1000, H = 600, CX = W / 2, CY = H / 2;
const COLOR = { positive: "#0F7B3E", negative: "#B3261E", neutral: "#8A85A3" } as const;

const short = (s: string, n = 30) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

export default function Graph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const [hover, setHover] = useState<string | null>(null);

  const pos = useMemo(() => {
    const p: Record<string, { x: number; y: number; a: number }> = { subject: { x: CX, y: CY, a: 0 } };
    const engines = nodes.filter((n) => n.type === "engine");
    engines.forEach((e, i) => {
      const a = (2 * Math.PI * i) / Math.max(engines.length, 1) - Math.PI / 2;
      p[e.id] = { x: CX + 120 * Math.cos(a), y: CY + 120 * Math.sin(a) * 0.8, a };
    });
    engines.forEach((e) => {
      const kids = edges.filter((x) => x.source === e.id && x.kind === "evidence").map((x) => x.target);
      const spread = Math.min(0.9, 0.3 * kids.length);
      kids.forEach((k, j) => {
        const a = p[e.id].a + (kids.length === 1 ? 0 : (j / (kids.length - 1) - 0.5) * 2 * spread);
        const r = 215 + (j % 2) * 24;
        p[k] = { x: CX + r * Math.cos(a) * 1.45, y: CY + r * Math.sin(a) * 1.0, a };
      });
    });
    nodes.filter((n) => n.type === "contradiction").forEach((c, i) => {
      const linked = edges.filter((x) => x.source === c.id && p[x.target]).map((x) => p[x.target]);
      if (linked.length) {
        const mx = linked.reduce((s, q) => s + q.x, 0) / linked.length;
        const my = linked.reduce((s, q) => s + q.y, 0) / linked.length;
        p[c.id] = { x: CX + (mx - CX) * 0.6, y: CY + (my - CY) * 0.6 + (i % 2 ? 22 : -22), a: 0 };
      } else p[c.id] = { x: CX, y: CY + 90 + i * 30, a: 0 };
    });
    return p;
  }, [nodes, edges]);

  const active = (id: string) => !hover || hover === id || edges.some((e) => (e.source === hover && e.target === id) || (e.target === hover && e.source === id));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Evidence graph">
      {edges.map((e, i) => {
        const a = pos[e.source], b = pos[e.target];
        if (!a || !b) return null;
        const conflict = e.kind === "conflict";
        return (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={conflict ? "#B3261E" : "#CDBF9F"} strokeWidth={conflict ? 1.6 : 1}
                strokeDasharray={conflict ? "5 4" : undefined}
                opacity={hover ? (hover === e.source || hover === e.target ? 1 : 0.12) : 1} />
        );
      })}
      {nodes.map((n, i) => {
        const p = pos[n.id];
        if (!p) return null;
        const col = n.type === "contradiction" ? "#B3261E" : n.type === "subject" ? "#E8761A" : n.type === "engine" ? "#1A1633" : COLOR[n.signal || "neutral"];
        const r = n.type === "subject" ? 34 : n.type === "engine" ? 22 : n.type === "contradiction" ? 15 : 11;
        const left = p.x < CX;
        return (
          <g key={n.id} className="pop" style={{ animationDelay: `${Math.min(i * 45, 900)}ms`, opacity: active(n.id) ? 1 : 0.2, cursor: "default" }}
             onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}>
            <title>{n.label}</title>
            {n.type === "contradiction" ? (
              <polygon points={`${p.x},${p.y - r} ${p.x + r},${p.y + r * 0.8} ${p.x - r},${p.y + r * 0.8}`} fill="#FADDD9" stroke={col} strokeWidth="2" />
            ) : (
              <circle cx={p.x} cy={p.y} r={r} fill={n.type === "subject" ? "#FDEBD6" : n.type === "engine" ? "#F3EAD7" : "#FFFDF8"} stroke={col} strokeWidth={n.type === "evidence" ? 2.5 : 2} />
            )}
            {n.type === "contradiction" && <text x={p.x} y={p.y + 6} textAnchor="middle" fontSize="14" fontWeight="700" fill={col}>!</text>}
            {n.type === "subject" && <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize="10" fontFamily="DM Mono, monospace" fill={col}>{short(n.label, 11).toUpperCase()}</text>}
            {n.type === "engine" && <text x={p.x} y={p.y + 3.5} textAnchor="middle" fontSize="8.5" fontFamily="DM Mono, monospace" fill="#1A1633">{short(n.label.replace("Google ", ""), 8)}</text>}
            {(n.type === "evidence" || n.type === "contradiction") && (
              <text x={p.x + (left ? -(r + 6) : r + 6)} y={p.y + 4} textAnchor={left ? "end" : "start"} fontSize="11" fill={n.type === "contradiction" ? "#B3261E" : "#4A4566"} fontFamily="Hind, sans-serif">
                {short(n.label, 26)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
