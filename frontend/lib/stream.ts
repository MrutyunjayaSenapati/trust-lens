import { StreamEvent } from "./types";

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function* investigate(
  body: { text: string; image_base64?: string; image_mime?: string; image_url?: string },
  signal?: AbortSignal
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API}/api/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Backend returned ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, i);
      buf = buf.slice(i + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (line) yield JSON.parse(line.slice(6)) as StreamEvent;
    }
  }
}
