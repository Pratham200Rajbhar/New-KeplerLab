# Task: Implement YT Video Voice Live Translation Feature

## Before You Start
Read and fully understand the implementation plan MD file in the codebase root before writing anything. Every architectural decision, service design, file structure, and integration point is already defined there. Also read the existing codebase to understand current patterns — routes, services, worker, hooks, API wrappers, config, Prisma schema — and match them exactly.

---

## Rules
- Follow the coding style, naming conventions, and folder structure of the existing codebase precisely
- Do not deviate from the plan
- Implement in the exact order defined in the plan — backend first, frontend second
- Every new service, route, hook, and component must mirror the pattern of its existing counterpart in the codebase
- Do not add any new npm packages — YouTube IFrame API loads via script tag injection
- Install backend dependencies: `pip install whisperx pyrubberband soundfile librosa` and `apt-get install -y rubberband-cli`

---

## UI Design

### Session Creation Dialog
Matches the existing dialog style in the codebase — same card, header, and button styling.

```
┌─────────────────────────────────────────────┐
│  🌐  YT Voice Translator                    │
│  Translate any YouTube video into your      │
│  language with synchronized audio           │
├─────────────────────────────────────────────┤
│                                             │
│  [ Paste YouTube URL...                 ]   │
│                                             │
│  ┌──────────────┐  Title of video here      │
│  │  Thumbnail   │  Duration: 12:34          │
│  │   Preview    │  Language: Auto-detected  │
│  └──────────────┘                           │
│                                             │
│  Source Language    [Auto-detect  ▾]        │
│  Translate To       [Select language ▾]     │
│  Voice              [Select voice    ▾]     │
│                     ○ Female  ○ Male        │
│                                             │
│  ⚠ Estimated processing: ~45 seconds       │
│  ⚠ Estimated tokens: ~2,400                │
│                                             │
│         [ Cancel ]  [ Start Translation ]   │
└─────────────────────────────────────────────┘
```

**Behavior:**
- Green checkmark on valid YouTube URL paste
- Thumbnail + title load via YouTube oEmbed automatically (no backend call)
- Orange warning if video exceeds 2 hours
- Red token warning if approaching daily limit
- Submit button disabled until language and voice are selected
- On submit: spinner with "Preparing pipeline..."

---

### Playback View
Full-width panel replacing the dialog — not a modal. Renders as the main content area.

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back   "Video Title"                🌐 EN → हिंदी  [Aria ▾] │
├───────────────────────────────┬─────────────────────────────────┤
│                               │                                 │
│                               │   TRANSLATED SUBTITLES          │
│   YouTube iframe              │                                 │
│   (muted, controls visible)   │  "नमस्ते, आज हम बात करेंगे     │
│                               │   **आर्टिफिशियल इंटेलिजेंस**   │
│                               │   के बारे में..."               │
│                               │                                 │
│                               │   [ word-level highlight ]      │
│                               │                                 │
├───────────────────────────────┴─────────────────────────────────┤
│                                                                  │
│  [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  │
│   green=ready   yellow=processing   grey=pending                 │
│                                                                  │
│  ⏮  ⏪  ▶  ⏩  ⏭    ━━━━●━━━━━━━━━━━━━━━  04:32 / 12:34       │
│                                                                  │
│  Speed: [0.75x] [1x✓] [1.25x] [1.5x]       [↓ Download SRT]    │
│                                                                  │
│  🔵 Buffered: 4 segments ahead  |  Sync: ✅ Good                │
└──────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Left pane (60%): muted YouTube iframe — user sees video, hears translated audio
- Right pane (40%): translated text with active word highlighted in primary accent color, previous words muted grey, smooth auto-scroll, minimum 18px font
- Segment readiness bar: hover shows tooltip with segment time range and status; clicking seeks to that segment
- Play/Pause syncs iframe and Web Audio API simultaneously
- Speed applies to both iframe (`player.setPlaybackRate()`) and audio playback rate
- Download SRT generates subtitle file client-side from word timestamps — no backend call
- Sync status turns ⚠️ if drift exceeds 800ms
- Shows "⏳ Buffering translated audio..." when seeking to an unprocessed segment
- Mobile: subtitle pane stacks below video, controls collapse to icon-only row

---

## Definition of Done
- [ ] Session creation accepts a YouTube URL and returns metadata
- [ ] Background job downloads, segments, translates, and synthesizes all segments
- [ ] Manifest endpoint returns real-time segment statuses
- [ ] Segment audio endpoint returns a playable MP3
- [ ] Player plays muted YouTube video with synchronized translated audio overlay
- [ ] Subtitle pane shows word-level highlighted text in real-time sync
- [ ] Segment readiness bar updates live via WebSocket
- [ ] Speed control affects both video and audio simultaneously
- [ ] Download SRT produces a valid subtitle file
- [ ] Seeking to an unprocessed segment triggers on-demand priority generation
