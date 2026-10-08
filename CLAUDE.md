# TrustLens: project context for Claude Code

## Why this project exists (the motive)
Entry for the **SerpApi India Hackathon 2026** (https://serpapi.github.io/serpapi-india-hackathon-2026/).
**Goal: win a top prize** (1st = ₹1,00,000) or Best in Track. **Deadline: Oct 10, 2026, 23:59 IST.** Solo/small team, India residents.

TrustLens answers "is this job offer / seller / deal real?" for ordinary Indians (students, job seekers, family WhatsApp groups) by cross-checking a pasted message against **live Google data via SerpApi**, then showing an explainable evidence trail.

### Judging criteria (unweighted, judged by SerpApi staff)
Idea strength · Originality · Technical complexity · Usefulness to the intended user · **Meaningful use of SerpApi data**.
Rules that matter: SerpApi must be central, not an afterthought; unfinished/non-functional/inaccessible projects are rejected; exposing API keys is grounds for disqualification; AI tools must be disclosed (Claude for code, Gemini at runtime). Full rules: https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html
Tracks: AI Agents, Open-Source Integrations, Travel & Local Discovery, Commerce & Market Intelligence, Knowledge & Public Interest, Open Innovation. Our pick: **Knowledge & Public Interest** (or AI Agents).

### Deliverables still needed
Public GitHub repo with setup instructions · demo video < 3 min showing it running locally · project description (what, who it helps, how SerpApi is used, track) · AI-tools disclosure.

## Differentiators (protect these when changing code)
1. **Multi-engine evidence**: google, google_news, google_maps, google_jobs, google_shopping, google_lens, each answering a distinct question.
2. **Contradiction detection** across sources (`reasoner.py`, collectors), e.g. real company + role not listed + recruiter email off the official domain = impersonation.
3. **Deterministic, explainable score**: 50 + sum of evidence/contradiction weights, clamped 0-100. Gemini NEVER changes the score or verdict; it only writes explanation, next steps and the EN/HI shareable warning.
4. **Credit-aware**: every SerpApi/Gemini response is cached in SQLite; one failing engine must never break an investigation.

## Architecture
- `backend/` FastAPI (Python 3.10+). `app/pipeline.py` orchestrates: `extraction.py` (Gemini + regex fallback + `red_flags` text patterns) → plan → `collectors.py` (parallel, one per engine) → `reasoner.py` (cross-source contradictions, score, verdict, confidence) → `synthesis.py` (Gemini briefing with fallback). Streams events over SSE at `POST /api/investigate`. `serp.py` and `gemini.py` are thin httpx clients (no SDKs). `mock.py` gives canned SerpApi data when `MOCK_MODE=1`.
- `frontend/` Next.js 14 (App Router, Tailwind 3, standalone output). Browser calls the API directly via `NEXT_PUBLIC_API_URL` (build-time). `components/Graph.tsx` draws the evidence graph in plain SVG; `Gauge.tsx` the score.
- Docker: `docker-compose.yml` runs both; keys come from `.env` (never commit; see `.env.example`).

## Commands
- Offline dev (no keys/credits): `MOCK_MODE=1`. Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000`. Frontend: `cd frontend && npm install && npm run dev`.
- Tests: `cd backend && pytest` (all offline). Frontend type-check: `cd frontend && npx tsc --noEmit`.
- Full stack: `docker compose up --build` → UI :3000, API :8000.
- Note: if developing from a mounted/synced Windows folder, run pytest from a copy; pytest's temp cleanup can fail on mounts.

## Status (as of Oct 8, 2026)
- DONE and verified offline: backend pipeline, 6 passing tests, Next.js build + type-check, UI rendered in headless Chromium against mock data.
- NOT yet verified: live Gemini calls, live SerpApi calls, `docker compose up` (Docker was unavailable in the build environment), the "fake discount" example (needs Gemini to extract `product`/prices; the regex fallback only detects job-style messages).
- Known gaps / ideas, in priority order:
  1. Run all 3 examples with real keys; tune weights in `collectors.py` if verdicts look wrong; confirm SerpApi response field names for each engine against live output.
  2. Strengthen `heuristic_entities` for deals (price/product regex) so the fallback is not job-only.
  3. Add frontend loading/empty states polish, a "re-run from cache" indicator, mobile layout check.
  4. Optional: Lens check from uploaded screenshots (needs a public image URL today).
  5. Record demo (lead with the "real brand, fake recruiter" example), write submission text, push public repo.

## Conventions
- Keep SerpApi usage central and visible; every evidence item should carry source links when available.
- Never log or commit keys; Gemini model name is configurable via `GEMINI_MODEL`.
- Prefer small, tested changes; this is a 2-day sprint, so finished beats ambitious.

## Update (Oct 8, 2026, later)
- Verified live: Gemini + SerpApi + Docker (backend and frontend as separate images). Gemini 2.5-flash is retired for new keys; default is `gemini-3.8-flash` with a fallback chain (`GEMINI_FALLBACK_MODELS`) in `gemini.py`.
- Added: link-only input resolved via SerpApi (`urlintel.py`; live happy path on a real indexed LinkedIn job NOT yet verified), deal heuristics without Gemini, Hindi explanation/steps, screenshot transcript feeding text red-flags, official-domain picked by frequency (fixes infosys.org vs infosys.com), `/api/benchmark` + `app/benchmark/` (cases, runner; results.json is empty until the runner is executed).
- Frontend redesigned ("modern Indian editorial": paper/indigo/saffron, pallu border, chakra-style dial, rubber-stamp verdict), EN/HI UI toggle, WhatsApp share + canvas share card, PWA with Web Share Target (`public/manifest.webmanifest`, `public/sw.js`, `app/icons/[size]`), `/benchmark` page.
- Dockerfile uses `npm install` (a Windows-generated lockfile breaks `npm ci` on Linux).
- Local Python 3.14 cannot install pinned deps (pydantic 2.10.4 has no wheel); run backend and tests via Docker (Python 3.11).
