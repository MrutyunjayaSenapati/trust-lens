# TrustLens

**Is this job offer, seller or deal real?** Paste a suspicious message and TrustLens investigates it against live Google data from [SerpApi](https://serpapi.com), then explains its verdict with a linked evidence trail.

Built for the SerpApi India Hackathon 2026. Track: AI Agents / Knowledge & Public Interest.

## How it works

0. **Links**: if you paste only a link (LinkedIn job, Naukri, a shop page), SerpApi's `google` engine finds what Google knows about that URL, so the company and role can still be checked. TrustLens never scrapes the page itself.
1. **Extract** (Gemini, with automatic fallback across several Gemini models, then a regex fallback): pulls out company, role, city, address, email, prices and whether money is demanded. Works on pasted text, links or a WhatsApp screenshot (Gemini reads it), in English, Hindi or Hinglish.
2. **Plan**: chooses which SerpApi engines to run from what was found.
3. **Collect** (SerpApi, in parallel, cached in SQLite):

| Engine | Question it answers |
|---|---|
| `google` | Are there scam reports? Does an official site exist? Does the recruiter's email domain match it? |
| `google_news` | Is the name tied to fraud or arrests in the news? |
| `google_maps` | Does the claimed office exist, is it a residential address, does it match the message? |
| `google_jobs` | Is the role actually listed publicly by that company? |
| `google_shopping` | Is the price far below market, is the "original price" inflated? |
| `google_lens` | Is the image reused across many unrelated sites? |

4. **Cross-examine**: rule-based reasoning compares sources and flags contradictions, e.g. *"the company is real (Maps + official site) but the role isn't listed and the recruiter's domain differs, which matches brand impersonation."*
5. **Score**: the 0-100 trust score is **deterministic** (every point traces to a piece of evidence). Gemini only writes the explanation and the shareable warning (English + Hindi); it cannot change the verdict.

## Run it

```bash
cp .env.example .env     # add SERPAPI_API_KEY and GEMINI_API_KEY
docker compose up --build
# UI  → http://localhost:3000
# API → http://localhost:8000/api/health
```

Backend and frontend are separate images, so you can run them independently:

```bash
docker build -t trustlens-backend ./backend
docker run -d --name tl-backend --env-file .env -e CORS_ORIGINS=http://localhost:3000 -p 8000:8000 -v trustlens-cache:/app/data trustlens-backend

docker build -t trustlens-frontend --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 ./frontend
docker run -d --name tl-frontend -p 3000:3000 trustlens-frontend
```

`NEXT_PUBLIC_API_URL` is baked in at build time and must be reachable from the user's browser.

Without Docker:

```bash
# backend (Python 3.10+)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000
# frontend (Node 20+)
cd frontend && npm install && npm run dev
```

Offline mode (no keys, no credits): set `MOCK_MODE=1` in `.env`, then use the built-in examples.

Tests: `cd backend && pytest` (all offline).

## Features worth knowing about
- **Hindi / English UI** with Gemini-written explanations in both languages.
- **Share to WhatsApp**: one tap opens WhatsApp with the warning, or download a ready-made verdict card image.
- **Installable PWA with share target**: install it from the browser menu, then on Android *Share → TrustLens* from WhatsApp or any app to check a message. Needs HTTPS (or localhost); iOS Safari does not support share targets.
- **Score ledger**: every point added or removed is listed, so the verdict is explainable.
- **Accuracy page** (`/benchmark`): results on labelled scam and genuine messages. Regenerate with:

```bash
docker exec tl-backend python -m app.benchmark.runner   # uses SerpApi credits, then cached
docker cp tl-backend:/app/app/benchmark/results.json backend/app/benchmark/results.json
```

- **Model fallback**: set `GEMINI_MODEL` and optionally `GEMINI_FALLBACK_MODELS` (comma separated). A 503/429/404 hops to the next model instead of failing.
- **Optional: Gemini via Vertex AI** (local development, uses your Google Cloud project's quota instead of the API key's). Run `gcloud auth application-default login`, set `GEMINI_VERTEX_PROJECT` in `.env`, and in Docker mount the credentials:

```bash
docker run ... -v "%APPDATA%\gcloud:/gcloud:ro" -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json trustlens-backend
```

  Vertex is tried first, then the API key. Without either, extraction falls back to deterministic rules.

## Notes
- Responses are cached in SQLite, so re-running a case uses 0 credits.
- A failing engine is skipped and reported; the investigation still completes with lower confidence.
- Absence of scam reports is only a weak positive signal. TrustLens is decision support, not proof. Report fraud at cybercrime.gov.in or 1930.
