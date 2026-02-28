<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# KeplerLab — AI Live Podcast Feature: Complete Plan


***

## What This Feature Is

An interactive, two-AI-host podcast experience where two AI personas hold a structured conversation about your selected learning material. You listen like a real podcast, interrupt anytime to ask questions, resume exactly where you paused, and walk away with a full transcript, doubt history, and exportable record — in any language, with any voice combination you choose.

This is not a static audio file. It is a living, responsive learning session.

***

## Core Capabilities

- Two distinct AI personas (Host + Guest Expert) conversing naturally
- Full Resource mode and Specific Topic mode
- Interrupt at any moment — ask by typing or speaking
- Unlimited follow-up questions per interruption
- AI detects when you are satisfied and resumes automatically
- Manual resume always available as override
- Podcast resumes from the exact segment it paused at
- Seek forward and backward like an audio player
- Chapter-based navigation
- Full multilingual support — every layer speaks the same language
- Male and female voice selection per persona
- Transcript, audio segments, and doubt history all saved permanently
- Export as PDF or JSON
- Doubt history converted to flashcards in one tap
- Bookmarks, speed control, annotations, and session library included

***

## Session Lifecycle

Every podcast session moves through clearly defined states:

```
CREATED
  └─► SCRIPT GENERATING
        └─► AUDIO GENERATING
              └─► READY
                    └─► PLAYING
                          ├─► PAUSED (Q&A)
                          │     └─► ANSWERING
                          │           └─► SATISFACTION CHECK
                          │                 ├─► PLAYING (auto-resume)
                          │                 └─► PAUSED (more questions)
                          └─► COMPLETED
```

Each state is persisted to the database. If the user closes the browser and returns later, the session picks up from the exact same state and segment.

***

## Two Modes of Content

### Full Resource Mode

The AI covers the entire uploaded source material. It retrieves representative content from across all topics in your source, generates a structured dialogue that organically flows through concepts, and produces a complete overview podcast.

### Specific Topic Mode

You define a topic before generation. The AI retrieves only the chunks most relevant to that topic from your source and builds the entire dialogue strictly around it. Content outside the topic scope is ignored.

***

## How AI Reads Your Source Material

The AI does not read your raw file at podcast time. Your material is already indexed when you uploaded it — extracted, chunked, embedded, and stored in ChromaDB. At podcast generation time:

**Retrieval phase:**

- A broad query is run against your indexed chunks
- ChromaDB returns the top 10 most relevant chunks via vector similarity
- The BGE Reranker re-scores those 10 by true semantic relevance
- Context Builder filters out short or noisy chunks and trims to the token limit
- Context Formatter assembles the final context as numbered references

**What gets sent to the LLM:**
The assembled numbered context — dense, relevant excerpts from your source — is what the AI script generator receives. It reads nothing outside this context window.

**Token budget for podcast:**
Higher than standard chat — up to 12,000 tokens of context — to ensure comprehensive coverage of the material.

***

## Two-Agent Dialogue System

Two personas are defined in the script generation prompt:


| Persona | Role | Speaking Style |
| :-- | :-- | :-- |
| **HOST** | Curious guide | Introduces topics, asks "why", "how", "what does that mean in practice" — drives the narrative forward |
| **GUEST Expert** | Subject matter expert | Answers deeply, gives examples, connects ideas, explains mechanisms — delivers the actual knowledge |

**Script structure:**

- Generated as a structured JSON array of turns: `[{speaker, text, segment_index}]`
- Each segment is approximately 80–120 words — roughly 30 to 60 seconds of speech
- The GUEST only speaks what is in the retrieved source chunks — no outside knowledge added
- If a concept is not in the source, the GUEST says it is not covered rather than fabricating
- LLM temperature is set to 0.7 (Creative preset) — language is natural, flowing, and engaging

**Engagement quality:**
The script prompt instructs the AI to include natural discussion hooks — moments where the HOST pauses to reflect, asks the GUEST to elaborate, or draws an analogy — so the dialogue feels like a real podcast and not a robotic recitation.

***

## Audio Generation

**Per-segment synthesis:**
Each dialogue turn is synthesized into its own audio file independently. Segments are not merged into one large file. This enables instant seek, individual replay, and crash-safe recovery.

**Parallel generation:**
All segments are synthesized simultaneously rather than one after another. A 20-segment podcast that would take 90 seconds serially completes in approximately 15 seconds.

**Storage:**
Each segment stored at: `output/podcast/{session_id}/seg_{index}_{speaker}.mp3`

**Duration tracking:**
Each segment's duration in milliseconds is stored at synthesis time. This allows the full timeline to be computed without playing the audio first.

***

## Voice System

### Voice Map

A config dictionary maps every supported language to four voices — two male, two female. Each voice has a name, gender, character description, and a preview text in that language.

### Voice Selection Rules

- HOST and GUEST are picked independently
- Any gender combination is allowed (male+male, female+female, or mixed)
- HOST and GUEST cannot be assigned the same voice — the second picker grays out the already-selected voice
- If both voices are the same gender, the system shows a soft warning: "Voices may sound similar"
- Voice selection is locked for the entire session — no voice changes mid-podcast


### Default Voice Pairs

If user skips selection:


| Language | HOST (Default) | GUEST (Default) |
| :-- | :-- | :-- |
| English | Guy — Male | Jenny — Female |
| Hindi | Madhur — Male | Swara — Female |
| Gujarati | Niranjan — Male | Dhwani — Female |
| Spanish | Alvaro — Male | Elvira — Female |
| Arabic | Hamed — Male | Zariyah — Female |
| French | Henri — Male | Denise — Female |
| German | Conrad — Male | Katja — Female |
| Japanese | Keita — Male | Nanami — Female |
| Chinese | Yunxi — Male | Xiaoxiao — Female |
| Portuguese | Antonio — Male | Francisca — Female |

### Voice Preview

Before generation, each voice has a Preview button that plays a 5-second sample inline — no modal, no page navigation.

***

## Multilingual Support — End to End

Every single layer of the pipeline respects the selected language:


| Layer | Behavior |
| :-- | :-- |
| Script generation | LLM prompt instructs: "Write the full dialogue in [language], natural spoken style" |
| TTS synthesis | Language-native neural voices used — no English voices on Hindi content |
| Mic input (STT) | Whisper receives language code hint for faster, accurate transcription |
| Q\&A answering | RAG answer prompt prefixed with "Answer in [language]" |
| Satisfaction detection | Heuristic dictionary per language — e.g., "okay / got it / theek hai / samajh gaya / hǎo de" |
| Transcript display | Rendered as-is — Devanagari, Arabic (RTL), CJK all display correctly |
| PDF export | NotoSans Unicode font family — all scripts render without breaking layout |

**Code-switching:**
Neural voices from edge-tts handle mixed-script content naturally. English technical terms within a Hindi or Gujarati sentence are pronounced correctly without extra configuration.

**Language change rule:**
Changing language after selecting voices automatically resets both voice selections to that language's defaults — prevents silent mismatched selections.

***

## Interrupt and Q\&A System

### How Interruption Works

1. User taps the ⚡ Interrupt button — always visible during playback
2. Podcast pauses immediately at the current segment
3. A drawer slides up from the bottom — text input and mic button both available
4. User types a question or holds the mic button to speak
5. Spoken audio is streamed to the backend and transcribed by Whisper
6. The question is routed through the RAG pipeline scoped to the same material
7. Answer is generated at temperature 0.2 (precise, grounded — not creative)
8. Answer is synthesized to audio using the GUEST voice
9. Answer text and audio are delivered back to the user
10. User can ask follow-ups indefinitely

### Podcast Speech vs Q\&A Speech

|  | Podcast Dialogue | Q\&A Answer |
| :-- | :-- | :-- |
| Temperature | 0.7 — creative, flowing | 0.2 — precise, factual |
| Style | Conversational narrative | Direct explanation |
| RAG query | Broad topic coverage | Exactly your question |
| Voice | HOST or GUEST persona | GUEST voice |
| Goal | Deliver the learning story | Satisfy your specific doubt |

### Satisfaction Detection

Two-layer system to determine when to auto-resume:

**Layer 1 — Heuristic (fast, no LLM call):**
Checks the user's message against a multilingual dictionary of satisfaction phrases. If confidence is ≥ 0.85 — auto-resume immediately.

**Layer 2 — LLM Classifier (only on ambiguous messages):**
A short structured LLM call: "Does this message indicate the user is satisfied? Yes/No." Runs only when Layer 1 is uncertain — approximately 20% of responses.

**If still unclear:**
WebSocket sends a gentle prompt to the frontend: "Ready to continue the podcast?" — two buttons: Resume / Ask More. User is never trapped.

**Manual Resume:**
Always available as a button. Pressing it immediately resumes regardless of satisfaction detection state. User has full control at all times.

### Resume Behavior

The podcast resumes from the exact segment number where it was paused. Nothing is repeated, nothing is skipped, no recap is generated unless the user explicitly asks for one.

***

## Playback Controls

Segment-aware player — not purely time-based:


| Control | Behavior |
| :-- | :-- |
| Play / Pause | Standard |
| Next Segment | Jumps to the next dialogue turn |
| Previous Segment | Goes back to the previous turn |
| Seek bar | Shows full timeline with chapter tick marks |
| Tap transcript line | Instantly seeks to that segment |
| Tap chapter tick | Jumps to that chapter |
| Speed control | Tap the speed label to cycle: 0.75x → 1x → 1.25x → 1.5x → 2x |
| Bookmark (🔖) | One tap drops a bookmark on the current segment — optional short label |

**Lookahead buffering:**
The frontend always pre-fetches the next 2 segments while the current one plays — eliminates any gap between segments and makes the experience feel seamless.

***

## Chapters

Automatically generated during script creation. The LLM is instructed to divide the podcast into named chapters (e.g., "Introduction", "Core Concepts", "Deep Dive", "Practical Applications", "Summary"). Chapter names and their starting segment indices are returned alongside the script.

Chapters appear as:

- Named tick marks on the seekbar
- A chapter bar at the top of the player showing the current chapter
- A chapter jump menu accessible by tapping the chapter name

***

## Additional Features

### Bookmarks

Tap 🔖 during playback to drop a bookmark on the current segment. Optionally add a short label. Bookmarks appear as markers on the seekbar and as highlighted lines in the transcript. Saved permanently with the session.

### Highlight and Annotate

Tap any transcript line to highlight it. Optionally attach a short personal note. Stored as annotation metadata per segment. Visible in exports.

### Estimated Listen Time

Displayed before playback starts — computed from total stored segment durations. Example: "~14 min listen". No computation needed at display time — it is a sum of already-stored values.

### Speed Control

Browser native playback rate — zero backend involvement. Speed preference persisted in local storage per session.

### Podcast Summary Card

Generated on demand or automatically at session end. One LLM call using the full transcript as input. Returns: key concepts covered, main takeaways, questions you asked. Included in exports.

### Doubt Flashcards

After session, one-tap converts the entire doubt history (your questions + AI answers) into flashcards using the existing flashcard generator. The doubt history is already structured text — it routes directly to the existing tool.

### Session Naming and Tags

Users can rename a session and add tags (e.g., "Exam Prep", "Quick Review"). Sessions are filterable and searchable in the Session Library.

### Auto-Pause on Tab Switch

When the browser tab is hidden, the podcast pauses automatically. Resumes when the user returns. Prevents missed content.

### Replay Last Answer

A "Replay Answer" button in the Q\&A drawer re-plays the last AI answer audio without re-generating. The file is already saved — it is purely a replay action.

***

## Session Library

A "My Podcasts" section within the Podcast Studio tab shows all past sessions for the current notebook:

Each entry shows:

- Session title (auto-named or user-renamed)
- Date created
- Total duration
- Language and mode badge
- Last played position
- Resume button — goes directly to the exact segment

***

## Saved Data Per Session

| Data | What Is Saved |
| :-- | :-- |
| Transcript | Every dialogue turn, speaker-labeled, with timestamps |
| Audio segments | Each segment as individual MP3 files |
| Doubt history | Every question, the segment it paused at, full AI answer text, answer audio |
| Bookmarks | Segment index and optional label |
| Annotations | Segment index and note text |
| Summary card | Generated text when requested |
| Export files | PDF and JSON files when generated |


***

## Export

### PDF Export

- Header: notebook name, date, language, mode, total duration
- Full transcript with speaker labels and timestamps
- Chapter dividers
- Doubts section: each Q\&A in a clearly labeled block showing which segment it interrupted
- Bookmarks and annotations included
- Rendered with NotoSans font for full Unicode support


### JSON Export

Fully structured machine-readable file:

```
{
  session_metadata: { ... },
  chapters: [ ... ],
  segments: [ {index, speaker, text, duration_ms, bookmarked, annotations} ],
  doubts: [ {paused_at_segment, question, answer, timestamp} ],
  summary: { ... }
}
```

Designed for archiving, external tools, or feeding into other pipelines.

Both exports are generated as background jobs. A download link is delivered via WebSocket when ready — user is not blocked.

***

## Connection Architecture

### Two Channels

| Channel | Protocol | Purpose |
| :-- | :-- | :-- |
| REST API | HTTP | Session creation, state retrieval, audio file serving, export requests |
| WebSocket `/ws` | Persistent | All real-time events — play, pause, seek, interrupt, answers, resume signals, mic streaming |

The WebSocket is the existing `/ws` endpoint — podcast events are new event types on the same channel. No new socket infrastructure needed.

### WebSocket Events

| Direction | Event | Trigger |
| :-- | :-- | :-- |
| Frontend → Backend | `podcast_interrupt` | User taps ⚡ |
| Frontend → Backend | `podcast_question` | User submits typed question |
| Frontend → Backend | `podcast_audio_chunk` | Mic streaming (250ms chunks) |
| Frontend → Backend | `podcast_resume` | User taps Resume |
| Frontend → Backend | `podcast_seek` | User seeks to segment |
| Frontend → Backend | `podcast_play` / `podcast_pause` | Player controls |
| Backend → Frontend | `podcast_progress` | Generation progress updates |
| Backend → Frontend | `podcast_ready` | Generation complete, session playable |
| Backend → Frontend | `podcast_paused` | Confirmed pause at segment N |
| Backend → Frontend | `podcast_answer` | Q\&A answer ready |
| Backend → Frontend | `podcast_auto_resume` | Satisfaction detected |
| Backend → Frontend | `podcast_resume_prompt` | System unsure, asking user |
| Backend → Frontend | `podcast_export_ready` | Export file available |


***

## UI Plan

### Three Distinct States — Each Fully Replaces the Previous

**State 1 — Setup:**
Clean centered card. Mode toggle, topic field (appears only in Topic mode), language picker, voice pickers with preview buttons, one Generate button. Past sessions listed below.

**State 2 — Generation:**
Progress bar with human-readable status messages and estimated time remaining. No controls. A small persistent chip in the app corner shows progress if user navigates away. Auto-transitions to player when ready.

**State 3 — Player:**
Three zones — Chapter bar + action icons (top), Transcript (middle, ~60% height), Player bar (bottom). Nothing else.

### Persistent Mini-Player

When navigating away during playback, a small bar appears at the bottom of the entire app:
`🎙 [Session Title — Chapter Name]   ▶   ⚡   ████░░`
Three elements only. Tapping it returns to the full player.

### Interrupt Drawer

Slides up from the bottom. Player and transcript stay visible but dimmed above it. Text input and mic (press-and-hold) shown together. After answer arrives: answer text + audio play button + "Ask a follow-up" (outline) + "Resume Podcast" (filled, primary). Two buttons only.

### Doubt Markers in Transcript

Inline pills at the exact line where an interruption occurred. Tap to expand the full Q\&A. Tap again to collapse. Keeps the transcript clean by default.

### End-of-Session Card

Appears only when the podcast completes or user manually finishes:
Export PDF, Export JSON, Create Flashcards, Listen Again, Close.
Export is never shown mid-playback.

***

## New Data Models Required

| Model | Key Fields |
| :-- | :-- |
| `PodcastSession` | session ID, notebook ID, user ID, mode, topic, language, status, current segment index, host voice, guest voice |
| `PodcastSegment` | session ID, sequence index, speaker, text, audio URL, duration in milliseconds |
| `PodcastDoubt` | session ID, paused-at segment index, question text, question audio URL, answer text, answer audio URL, resolved timestamp |
| `PodcastExport` | session ID, format (PDF/JSON), file URL, created timestamp |


***

## New API Routes Required

| Method | Path | Purpose |
| :-- | :-- | :-- |
| POST | `/podcast/session` | Create session |
| GET | `/podcast/session/{id}` | Get full session state and segment list |
| POST | `/podcast/session/{id}/start` | Begin generation pipeline |
| GET | `/podcast/session/{id}/segment/{n}/audio` | Serve individual segment audio |
| GET | `/podcast/session/{id}/doubts` | Full Q\&A history |
| GET | `/podcast/session/{id}/bookmarks` | All bookmarks |
| POST | `/podcast/session/{id}/export` | Trigger PDF or JSON export |
| GET | `/podcast/export/{id}` | Download completed export |


***

## New Frontend Components Required

| Component | Purpose |
| :-- | :-- |
| `PodcastStudio` | Container — owns all session state and WebSocket connection |
| `PodcastModeSelector` | Setup screen — mode, topic, language, voice pickers |
| `PodcastGenerating` | Progress screen during generation |
| `PodcastPlayer` | Segment-aware player bar with all controls |
| `PodcastTranscript` | Auto-scrolling speaker-labeled transcript with inline doubt markers |
| `PodcastChapterBar` | Chapter names and seek ticks |
| `PodcastInterruptDrawer` | Q\&A input — mic + text + answer display + action buttons |
| `PodcastDoubtHistory` | Collapsible full Q\&A history (side panel) |
| `PodcastExportBar` | End-of-session export and flashcard options |
| `PodcastMiniPlayer` | Persistent bottom bar when navigating away |
| `PodcastSessionLibrary` | Past sessions list with resume |
| `VoicePicker` | Voice dropdown with gender filter and inline preview |


***

## New Context and Hooks Required

| Item | Purpose |
| :-- | :-- |
| `PodcastContext` | Global podcast state — session, segments, doubts, current index, playback status, interrupt state |
| `useMicInput` hook | MediaRecorder management — chunk capture, streaming, press-and-hold logic |
| `usePodcastWebSocket` hook | All WS event handling for podcast — maps event types to context state updates |
| `usePodcastPlayer` hook | Segment progression, lookahead prefetch, speed control, auto-advance logic |


***

## Implementation Phases

| Phase | What Gets Built | User Value Unlocked |
| :-- | :-- | :-- |
| **P1 — Foundation** | Session model, script generation, parallel TTS, basic segment playback | Listen to a two-AI podcast on any source |
| **P2 — Player** | Seek, chapter navigation, position persistence, live transcript sync, mini-player | Full audio player experience with seek and resume |
| **P3 — Interrupt System** | WebSocket interrupt flow, mic STT, RAG Q\&A, satisfaction detection, auto/manual resume | Ask questions mid-podcast, resume from exact point |
| **P4 — Multilingual + Voices** | Full voice map config, language-parameterized prompts, gender filter, voice preview, multilingual satisfaction detection | Complete language and voice customization |
| **P5 — Polish and Export** | Bookmarks, annotations, summary card, doubt flashcards, PDF/JSON export, session library, tags | Full session history, export, and learning utilities |


***

## Risk and Edge Cases

| Scenario | Handling |
| :-- | :-- |
| Generation fails mid-way | Session marked FAILED, user offered retry — checkpoint recovery from last completed segment |
| WebSocket disconnects during playback | Frontend auto-reconnects silently; current position synced from database on reconnect |
| Mic permission denied | System falls back to text-only input automatically — mic button grayed with tooltip |
| Satisfaction detector wrong | Manual Resume always overrides — user is never trapped in Q\&A state |
| Export takes long | Background job — user not blocked; WS pushes download link when ready |
| User navigates away during generation | Persistent chip tracks progress; WS event delivers notification when podcast is ready |
| Source has very little content | Minimum viable script enforced — system generates what it can and discloses coverage limit in session metadata |

