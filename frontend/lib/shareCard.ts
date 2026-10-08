import type { Lang } from "./i18n";
import type { Result, Verdict } from "./types";
import { VERDICT_COLOR } from "./verdict";

const W = 1080, H = 1350;

function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  // Split on spaces; Devanagari also uses spaces between words, so this works for both scripts.
  const words = text.replace(/\s+/g, " ").trim().split(" ");
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    const test = cur ? `${cur} ${w}` : w;
    if (ctx.measureText(test).width > maxW && cur) { lines.push(cur); cur = w; } else cur = test;
  }
  if (cur) lines.push(cur);
  return lines;
}

/** Draws a 1080x1350 WhatsApp-friendly verdict card and returns a PNG blob. Runs fully in the browser. */
export async function renderShareCard(
  result: Result, lang: Lang, stampText: string, warning: string, headline: string, footer: string
): Promise<Blob> {
  const hi = lang === "hi";
  try {
    await Promise.all([
      document.fonts.load("600 64px 'Fraunces Variable'"),
      document.fonts.load("500 34px Hind", warning),
      document.fonts.load("400 30px 'Tiro Devanagari Hindi'", stampText + headline),
      document.fonts.load("500 22px 'DM Mono'"),
    ]);
  } catch {}
  const canvas = document.createElement("canvas");
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext("2d")!;
  const v: Verdict = result.verdict;
  const { fg, wash } = VERDICT_COLOR[v];
  const display = hi ? "'Tiro Devanagari Hindi', Georgia, serif" : "'Fraunces Variable', Georgia, serif";

  // paper + tiranga strip
  ctx.fillStyle = "#FBF5E9"; ctx.fillRect(0, 0, W, H);
  const third = W / 3;
  ctx.fillStyle = "#E8761A"; ctx.fillRect(0, 0, third, 12);
  ctx.fillStyle = "#FFFDF8"; ctx.fillRect(third, 0, third, 12);
  ctx.fillStyle = "#138808"; ctx.fillRect(third * 2, 0, third, 12);

  // block-print border strip top + bottom
  const strip = (y: number) => {
    ctx.fillStyle = "#1A1633"; ctx.fillRect(0, y, W, 34);
    for (let x = 0; x < W; x += 60) {
      ctx.fillStyle = "#E8761A";
      ctx.beginPath(); ctx.moveTo(x + 14, y + 17); ctx.lineTo(x + 26, y + 5); ctx.lineTo(x + 38, y + 17); ctx.lineTo(x + 26, y + 29); ctx.fill();
      ctx.fillStyle = "#F2B21B"; ctx.beginPath(); ctx.arc(x + 52, y + 17, 7, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#138808"; ctx.beginPath(); ctx.arc(x + 52, y + 17, 3, 0, Math.PI * 2); ctx.fill();
    }
  };
  strip(12); strip(H - 46);

  // brand
  ctx.fillStyle = "#1A1633"; ctx.font = `600 44px ${"'Fraunces Variable', Georgia, serif"}`; ctx.textAlign = "left";
  ctx.fillText("Trust", 70, 130);
  const tw = ctx.measureText("Trust").width;
  ctx.fillStyle = "#E8761A"; ctx.fillText("Lens", 70 + tw, 130);
  const small = hi ? "500 26px Hind, sans-serif" : "500 22px 'DM Mono', monospace";
  ctx.fillStyle = "#8A85A3"; ctx.font = small; ctx.textAlign = "right";
  ctx.fillText(headline.toUpperCase(), W - 70, 128);

  // subject
  ctx.textAlign = "left"; ctx.fillStyle = "#1A1633";
  ctx.font = `600 54px ${display}`;
  const subject = result.entities.company || result.entities.product || "";
  if (subject) { ctx.fillText(subject.length > 28 ? subject.slice(0, 27) + "…" : subject, 70, 235); }
  ctx.font = "400 30px Hind, sans-serif"; ctx.fillStyle = "#4A4566";
  const sub = [result.entities.role, result.entities.city].filter(Boolean).join(" · ");
  if (sub) ctx.fillText(sub.slice(0, 48), 70, 282);

  // score dial
  const cx = 300, cy = 560, N = 24, lit = Math.round((result.score / 100) * N);
  ctx.fillStyle = "#FFFDF8"; ctx.beginPath(); ctx.arc(cx, cy, 215, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = "#E4D8BF"; ctx.lineWidth = 3; ctx.stroke();
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2 - Math.PI / 2;
    ctx.strokeStyle = i < lit ? fg : "#E4D8BF"; ctx.lineWidth = i < lit ? 13 : 9; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * 148, cy + Math.sin(a) * 148); ctx.lineTo(cx + Math.cos(a) * 200, cy + Math.sin(a) * 200); ctx.stroke();
  }
  ctx.fillStyle = "#1A1633"; ctx.textAlign = "center"; ctx.font = "600 130px 'Fraunces Variable', Georgia, serif";
  ctx.fillText(String(result.score), cx, cy + 36);
  ctx.fillStyle = "#8A85A3"; ctx.font = "500 24px 'DM Mono', monospace"; ctx.fillText("/ 100", cx, cy + 82);

  // stamp
  ctx.save();
  ctx.translate(790, 540); ctx.rotate(-0.1);
  ctx.font = `700 ${hi ? 56 : 60}px ${display}`;
  const sw = Math.max(300, ctx.measureText(stampText).width + 70);
  ctx.fillStyle = wash; ctx.strokeStyle = fg; ctx.lineWidth = 9;
  ctx.beginPath(); (ctx as any).roundRect(-sw / 2, -70, sw, 140, 22); ctx.fill(); ctx.stroke();
  ctx.lineWidth = 3; ctx.beginPath(); (ctx as any).roundRect(-sw / 2 + 14, -56, sw - 28, 112, 14); ctx.stroke();
  ctx.fillStyle = fg; ctx.textAlign = "center"; ctx.fillText(stampText, 0, 22);
  ctx.restore();

  // warning message panel
  const px = 60, py = 840, pw = W - 120;
  ctx.fillStyle = "#FFFDF8"; ctx.strokeStyle = "#E4D8BF"; ctx.lineWidth = 3;
  ctx.beginPath(); (ctx as any).roundRect(px, py, pw, 380, 26); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#1A1633"; ctx.textAlign = "left";
  let size = 36;
  let lines: string[] = [];
  for (; size >= 26; size -= 2) {
    ctx.font = `500 ${size}px Hind, 'Tiro Devanagari Hindi', sans-serif`;
    lines = wrap(ctx, warning, pw - 80);
    if (lines.length * size * 1.45 <= 320) break;
  }
  lines.slice(0, 8).forEach((l, i) => ctx.fillText(l, px + 40, py + 30 + size + i * size * 1.45));

  ctx.fillStyle = "#4A4566"; ctx.font = small; ctx.textAlign = "center";
  ctx.fillText(footer, W / 2, H - 70);

  return await new Promise((res, rej) => canvas.toBlob((b) => (b ? res(b) : rej(new Error("toBlob failed"))), "image/png"));
}
