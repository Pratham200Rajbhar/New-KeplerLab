# Implementation Prompt — AI Live Podcast Feature

## Context
You have the complete feature plan in `KeplerLab — AI Live Podcast Feature: Complete Plan.md`.
The existing codebase is fully documented in `docs.md`.
Read both before starting. Do not ask for clarification — all decisions are already made in the plan.

---

## What to Build

Implement the **AI Live Podcast** feature end to end as described in the plan.

---

## UI Placement

- Add a **Podcast tab** inside `StudioPanel.jsx` alongside the existing Quiz, Flashcards, and Presentation tabs
- The entire podcast experience lives in this right sidebar panel — no new pages, no new routes
- Behavior must be consistent with how other generation features work in StudioPanel:
  - Form inputs at the top
  - Generate button triggers background job
  - Results render below inside the same panel
- Three internal states inside the panel: **Setup → Generating → Player**
- Each state fully replaces the previous one inside the panel
- Mini-player persists at the bottom of the app when user switches tabs

---

## Backend

- Add all new routes under `/podcast/*` in a new `routes/podcast_live.py`
- Add all new services under `services/podcast/` extending the existing podcast folder
- Add new Prisma models: `PodcastSession`, `PodcastSegment`, `PodcastDoubt`, `PodcastExport`
- Reuse existing: RAG pipeline, edge-tts, Whisper, WebSocket manager, background worker, LLM service
- All new WebSocket events go through the existing `/ws` endpoint as new event types

---

## Frontend

- Add new components under `components/podcast/`
- Add `PodcastContext.jsx` to `context/`
- Add `useMicInput`, `usePodcastWebSocket`, `usePodcastPlayer` to `hooks/`
- Add `api/podcast.js` to `api/`

---

## Implementation Order

Follow phases exactly as defined in the plan:
1. P1 — Session model + script generation + TTS + basic playback
2. P2 — Seek + chapters + position persistence + transcript sync + mini-player
3. P3 — Interrupt + mic STT + RAG Q&A + satisfaction detection + resume
4. P4 — Multilingual + voice map + gender filter + voice preview
5. P5 — Bookmarks + annotations + summary card + doubt flashcards + export + session library

---

## Constraints

- Do not modify existing routes, services, or components
- Only extend and add new files
- Every layer must respect the selected language end to end
- Session state must survive browser refresh — always read from database on reconnect
- Manual resume always overrides satisfaction detection — no exceptions
