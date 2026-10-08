import { ImageResponse } from "next/og";

// PNG app icons for the PWA manifest, drawn at request time (no binary assets to commit).
export async function GET(req: Request, { params }: { params: { size: string } }) {
  const size = Math.min(1024, Math.max(48, parseInt(params.size, 10) || 192));
  const maskable = new URL(req.url).searchParams.get("maskable") === "1";
  const pad = maskable ? size * 0.2 : size * 0.1; // maskable icons need a safe zone
  const inner = size - pad * 2;
  const R = inner * 0.34;
  const spokes = Array.from({ length: 24 }, (_, i) => {
    const a = (i / 24) * Math.PI * 2;
    return (
      <line key={i} x1={50 + Math.cos(a) * 17} y1={50 + Math.sin(a) * 17} x2={50 + Math.cos(a) * 33} y2={50 + Math.sin(a) * 33}
            stroke="#F2B21B" strokeWidth={i % 2 ? 1.4 : 2.2} strokeLinecap="round" />
    );
  });
  return new ImageResponse(
    (
      <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", background: "#1A1633" }}>
        <div style={{ width: inner, height: inner, display: "flex", alignItems: "center", justifyContent: "center", background: "#FBF5E9", borderRadius: maskable ? inner * 0.5 : inner * 0.24 }}>
          <svg width={R * 2.6} height={R * 2.6} viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="none" stroke="#1A1633" strokeWidth="7" />
            {spokes}
            <circle cx="50" cy="50" r="9" fill="#E8761A" />
            <line x1="78" y1="78" x2="94" y2="94" stroke="#138808" strokeWidth="9" strokeLinecap="round" />
          </svg>
        </div>
      </div>
    ),
    { width: size, height: size }
  );
}
