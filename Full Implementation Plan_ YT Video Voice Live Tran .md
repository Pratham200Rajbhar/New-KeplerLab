<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Full Implementation Plan: YT Video Voice Live Translation

## Implementation Philosophy

Build in **5 sequential phases**, each independently deployable and testable. No phase breaks existing KeplerLab functionality. Every new service follows the exact same structural pattern already established in the codebase — routes, services, worker, WebSocket, Prisma.[^1]

***

## Phase 1 — Foundation \& Infrastructure (Week 1)

### 1.1 Prisma Schema Migration

Add two new models to `backend/prisma/schema.prisma`. Run `prisma migrate dev` after.

**`YTTranslationSession`** stores:

- Session identity: `id`, `userId`, foreign key to `User`
- Video metadata: `youtubeUrl`, `videoTitle`, `videoDurationMs`, `videoThumbnailUrl`
- Language config: `sourceLanguage` (nullable — null means auto-detect), `targetLanguage`, `voiceId`, `ttsProvider` (default `EDGE_TTS`)
- Pipeline state: `status` (enum: `pending | downloading | segmenting | pass1_glossary | processing | ready | failed`), `totalSegments`, `completedSegments`
- Quality metadata: `transcriptSource` (`whisper | youtube_api`), `glossaryPath` (filesystem path to session glossary JSON)
- Timestamps: `createdAt`, `updatedAt`

**`YTTranslationSegment`** stores:

- Identity: `id`, `sessionId` (FK), `segmentIndex`
- Timing: `startMs`, `endMs`, `originalDurationMs`, `ttsDurationMs`, `stretchRatio`, `syncDeltaMs`
- Content: `originalText`, `translatedText`, `alignmentQuality` (`precise | approximate`)
- File paths: `originalAudioPath` (temp), `translatedAudioPath` (permanent)
- Resilience: `status` (enum: `pending | transcribing | translating | synthesizing | aligning | stretching | ready | failed | dead`), `retryCount`, `errorDetail`, `lastAttemptAt`


### 1.2 Configuration Additions to `core/config.py`

Add these to the `pydantic-settings` `BaseSettings` class:


| Setting | Default | Purpose |
| :-- | :-- | :-- |
| `TTS_PROVIDER` | `EDGE_TTS` | Active TTS backend selector |
| `TTS_DEFAULT_RATE` | `+0%` | SSML baseline rate |
| `TTS_STRETCH_MIN` | `0.75` | WSOLA lower clamp |
| `TTS_STRETCH_MAX` | `1.35` | WSOLA upper clamp |
| `YT_MAX_DURATION_MINUTES` | `120` | Hard cap on video length |
| `YT_TRANSLATION_QUALITY_GATE` | `False` | Back-translation similarity check toggle |
| `YT_TRANSLATION_QUALITY_THRESHOLD` | `0.82` | Minimum semantic similarity score |
| `YT_SEGMENT_PRIORITY_WINDOW_S` | `60` | Seconds ahead of playhead to prioritize |
| `YT_MAX_SEGMENT_RETRIES` | `3` | Per-segment retry cap |
| `YT_CIRCUIT_BREAKER_THRESHOLD` | `5` | Consecutive failures before stage pause |
| `YT_CIRCUIT_BREAKER_PAUSE_S` | `30` | Circuit breaker cooldown duration |
| `SILERO_VAD_MODEL_PATH` | `data/models/silero_vad/` | Silero VAD weights location |
| `WHISPERX_MODEL_SIZE` | `turbo` | WhisperX model variant |
| `WHISPERX_ALIGNMENT_MODEL` | `wav2vec2` | Forced alignment backend |

### 1.3 Worker Job Type Registration

In `worker.py`, add `YT_TRANSLATION` to the `BackgroundJob.jobType` dispatch switch. The dispatch target is `pipeline.process_yt_translation_session(session_id)`. This inherits the existing crash-recovery reset logic, `MAX_CONCURRENT_JOBS` semaphore, and the notify-on-enqueue mechanism without modification.[^1]

### 1.4 Storage Directory Setup

Add to the startup directory creation in `main.py` lifespan:

```
data/output/yt_translation/              # Session root
data/output/yt_translation/{session_id}/ # Per-session audio files
data/models/silero_vad/                  # VAD model weights
data/models/whisperx/                    # WhisperX alignment models
```


***

## Phase 2 — TTS Provider Abstraction Layer (Week 1–2)

### 2.1 `services/tts_provider/schemas.py`

Define all Pydantic models for the provider contract:

**`VoiceConfig`**: `voice_id`, `language_code`, `gender`, `provider`

**`TTSRequest`**: `text`, `voice_config`, `options` (dict for SSML overrides)

**`WordTimestamp`**: `word`, `start_ms`, `end_ms`, `confidence`

**`TTSResult`**: `audio_bytes`, `duration_ms`, `sample_rate` (default 24000 Hz), `word_timestamps: List[WordTimestamp]`, `provider_used`, `alignment_source` (`forced_alignment | approximated`)

**`VoiceInfo`**: `id`, `display_name`, `language_code`, `gender`, `provider`, `latency_tier`

**`ProviderCapabilities`**: `supports_ssml`, `supports_streaming`, `supported_languages`, `latency_tier` (`low | medium | high`)

### 2.2 `services/tts_provider/base.py`

Abstract class with three methods, all `async`:

- `synthesize(request: TTSRequest) → TTSResult`
- `synthesize_streaming(request: TTSRequest) → AsyncGenerator[bytes]`
- `list_voices(language_code: str) → List[VoiceInfo]`
- `get_capabilities() → ProviderCapabilities`


### 2.3 `services/tts_provider/providers/edge_tts.py`

Concrete implementation of the abstract base. Key behavioral notes:

- Calls `edge_tts.Communicate(text, voice, rate="+0%").stream()` in async mode (not batch)
- Collects all audio bytes from the stream iterator
- **Does NOT estimate word timestamps** — returns empty `word_timestamps` list with `alignment_source="approximated"`. Real timestamps are injected by the forced aligner in Phase 3 as a post-processing step.
- `list_voices()` calls `edge_tts.list_voices()` and filters by `language_code` BCP-47 prefix
- `get_capabilities()` returns `latency_tier="low"`, `supports_ssml=True`, `supports_streaming=True`


### 2.4 `services/tts_provider/factory.py`

Single function `get_tts_provider() → TTSProvider` with `@lru_cache(maxsize=8)`. Reads `settings.TTS_PROVIDER`, maps to concrete class, returns singleton. Mirrors `llm_service/llm.py` exactly.[^1]

### 2.5 `services/tts_provider/voice_registry.py`

Single function `list_for_language(language_code: str) → List[VoiceInfo]`. Calls `get_tts_provider().list_voices(language_code)`. This is the only function the API route calls — frontend never references a provider directly.

***

## Phase 3 — Core Processing Services (Week 2–3)

### 3.1 `services/yt_translation/segment_splitter.py`

**Approach: Silero-VAD + natural boundary detection**

Process:

1. Load full downloaded audio via `librosa.load()` at 16kHz mono (VAD requirement)
2. Load Silero-VAD model from `settings.SILERO_VAD_MODEL_PATH` — load once, cache in module-level variable (same warm-up pattern as Whisper and reranker in `main.py` )[^1]
3. Run VAD inference → get frame-level speech probability timeline (10ms resolution)
4. Apply threshold: speech if probability > 0.5 for 3+ consecutive frames
5. Find silence gaps > 300ms between speech regions — these are candidate split points
6. Group speech regions into segments targeting 20–45s duration:
    - Prefer split at longest silence gap within the 20–45s window
    - If no silence gap found within 45s → force split at 45s with 500ms buffer overlap
    - Never create segments shorter than 8s (too short for translation context)
7. Output list of `{segment_index, start_ms, end_ms, preceding_silence_ms}` — all stored to `YTTranslationSegment` records
8. Run in `asyncio.run_in_executor` (non-blocking — librosa and VAD are synchronous CPU ops)

### 3.2 `services/yt_translation/transcript_resolver.py`

**Approach: Two-path with quality fallback**

**Fast path** (attempt first):

1. Call `youtube_transcript_api.get_transcript(video_id, languages=[source_lang, 'en'])`
2. If successful: returns segment-aligned text with coarse timestamps (sentence-level, not word-level)
3. Set `transcriptSource = "youtube_api"` on session
4. WhisperX forced alignment still runs on this transcript (Phase 3.4) — the transcript text is used as the alignment reference, audio provides the timing. This gives word-level timestamps even from caption text.

**Fallback path** (when captions unavailable or quality insufficient):

1. Extract audio segment file path
2. Call `whisperx.load_model(settings.WHISPERX_MODEL_SIZE)` — model pre-warmed at startup
3. Call `whisperx.transcribe(audio_path, language=source_lang)` — returns segments with coarse timestamps
4. Set `transcriptSource = "whisper"` on session
5. Pass to forced aligner (Phase 3.4) for word-level timestamps

**Quality check between paths**: If `youtube-transcript-api` returns text but the transcript has fewer than 3 words per 10 seconds (likely auto-generated garbage), fall back to Whisper.

### 3.3 `services/yt_translation/translation_service.py`

**Approach: Two-pass glossary-locked translation**

**Pass 1 — Glossary Extraction** (runs once per session on full transcript text):

- Concatenate all segment texts into full document
- Call `get_llm_structured()` at `temperature=0.1` with `yt_glossary_prompt.txt`
- Prompt instructs: extract proper nouns, technical terms, brand names, domain vocabulary; return as `List[{source_term, target_equivalent, part_of_speech}]`
- Store output as `session_glossary.json` in session directory
- Store filesystem path in `YTTranslationSession.glossaryPath`

**Pass 2 — Per-Segment Translation**:

Prompt context assembled in this exact order (token budget managed to keep total under 2000 tokens):

1. `{glossary}` — full session glossary JSON (locked terminology)
2. `{prev_segment_1}` — previous segment's translated text
3. `{prev_segment_2}` — two segments back translated text (for stylistic consistency)
4. `{next_preview}` — first sentence of next segment's source text (prevents cliff-edge sentence breaks)
5. `{current_segment}` — source text to translate

Call `get_llm_structured()` at `temperature=0.1` (NOT creative temperature — translation requires determinism) with structured output enforcing plain text response only.

**Quality gate** (when `YT_TRANSLATION_QUALITY_GATE=True`):

1. Translate output back to source language using a second LLM call
2. Compute semantic similarity between back-translation and original using the existing sentence-transformers cross-encoder in `rag/reranker.py`  — no new model needed[^1]
3. If similarity < `settings.YT_TRANSLATION_QUALITY_THRESHOLD` (0.82): retry translation with stricter prompt (`"Translate as literally as possible while remaining natural"`)
4. After 2 retries below threshold: accept best attempt, flag `segment.alignmentQuality = "approximate"`

### 3.4 `services/tts_provider/alignment/forced_aligner.py`

**Approach: WhisperX CTC forced alignment**

This module runs on **both** the original audio (to refine transcript timestamps) and the TTS-generated audio (to get translated word timestamps). Same function, different inputs.

Process:

1. Load `whisperx.load_align_model(language_code, device)` — one model per language, cached in a module-level dict keyed by language code
2. Call `whisperx.align(transcript_segments, alignment_model, audio, device)`
3. Output: `List[WordTimestamp]` with `{word, start_ms, end_ms, score}` at ±20–40ms accuracy
4. Filter out low-confidence alignments (score < 0.6) — mark those words as `approximate`
5. Attach result to `TTSResult.word_timestamps` with `alignment_source="forced_alignment"`

**Device strategy**: Use `gpu_manager.py` (already in your stack ) to decide `device="cuda"` vs `device="cpu"`. On CPU, WhisperX alignment for a 30s segment takes ~2s — acceptable within the latency budget.[^1]

### 3.5 `services/yt_translation/tts_synthesizer.py`

Process per segment:

1. Call `get_tts_provider().synthesize(TTSRequest(text=translated_text, voice_config=voice_config))` → raw `TTSResult` with empty word timestamps
2. Call `forced_aligner.align(tts_result.audio_bytes, translated_text, target_language)` → inject real `word_timestamps` into `TTSResult`
3. Pass to `timing_adjuster.adjust(tts_result, original_segment_duration_ms)` → returns time-stretched audio
4. Store final audio to `data/output/yt_translation/{session_id}/seg_{idx:04d}_translated.mp3`
5. Update `YTTranslationSegment`: `translatedAudioPath`, `audioDurationMs`, `stretchRatio`, `syncDeltaMs`

### 3.6 `services/yt_translation/timing_adjuster.py`

**Approach: WSOLA via pyrubberband**

Process:

1. Receive `tts_audio_bytes`, `tts_duration_ms`, `original_duration_ms`
2. Compute `stretch_ratio = original_duration_ms / tts_duration_ms`
3. Check clamp: `settings.TTS_STRETCH_MIN` (0.75) to `settings.TTS_STRETCH_MAX` (1.35)
4. If within clamp:
    - Convert bytes to numpy float32 array via `librosa.load()`
    - Call `pyrubberband.time_stretch(audio, sample_rate, stretch_ratio)`
    - Convert back to bytes via `soundfile.write()` to in-memory buffer
5. If outside clamp (extreme mismatch):
    - Apply max clamp stretch
    - Compute residual drift: `sync_delta_ms = stretched_duration - original_duration`
    - Store `syncDeltaMs` in DB for frontend compensation
    - Frontend inserts a silence buffer of `sync_delta_ms` before the next segment's scheduled start
6. Output: `{audio_bytes, final_duration_ms, stretch_ratio_applied, sync_delta_ms}`

### 3.7 `services/yt_translation/segment_cache.py`

**Redis key schema:**


| Key | TTL | Value |
| :-- | :-- | :-- |
| `yt:{sid}:meta` | 24h | Video metadata JSON |
| `yt:{sid}:glossary` | 24h | Session glossary JSON |
| `yt:{sid}:seg:{idx}:status` | 24h | Segment status string |
| `yt:{sid}:seg:{idx}:timestamps` | 24h | Word timestamp JSON |
| `yt:{sid}:manifest` | 24h | Full manifest JSON (rebuilt on each segment completion) |
| `yt:{sid}:progress` | 24h | `{total, completed, failed}` |
| `yt:{sid}:circuit:{stage}` | 30s | Circuit breaker active flag (TTL = breaker pause duration) |

Manifest is rebuilt as a complete JSON blob on every segment status change — cheap to write, extremely fast to read. Frontend polls this single key rather than querying the DB.

### 3.8 `services/yt_translation/pipeline.py`

**The main orchestrator — the only file that calls all others.**

**Startup sequence:**

1. Update session `status = "downloading"`
2. Run `yt-dlp --format bestaudio --no-playlist -o {audio_path}` via subprocess with timeout
3. Update `status = "segmenting"` → run `segment_splitter.split(audio_path)` → create all `YTTranslationSegment` DB records with `status="pending"`, update `totalSegments`
4. Update `status = "pass1_glossary"` → run full transcript resolve → run `translation_service.extract_glossary(full_transcript)`
5. Update `status = "processing"` → enqueue all segments into `asyncio.PriorityQueue`

**Priority queue management:**

- All segments start at priority 2 (background)
- First 3 segments promoted to priority 0 immediately (initial buffer fill)
- WebSocket message from frontend with `{event: "seek", position_ms: N}` triggers:
    - Clear priority 0 and 1 items from queue
    - Re-enqueue target segment window at priority 0
    - Remaining segments at appropriate priority based on distance from new position

**Per-segment worker coroutine:**

1. Dequeue segment from priority queue
2. Check circuit breaker Redis keys before each stage — if breaker active for that stage, wait `asyncio.sleep(breaker_remaining_ttl)`
3. Run each stage sequentially: `transcribe → translate → synthesize → align → stretch`
4. On any exception: increment `retryCount`, check against `YT_MAX_SEGMENT_RETRIES`
    - If below max: re-enqueue at priority 0 (retry immediately)
    - If at max: set `status="dead"`, store `errorDetail`, increment circuit breaker counter for failed stage
5. On success: set `status="ready"`, update `segment_cache`, call `ws_manager.send_to_user(user_id, {event: "yt_segment_ready", segment_index: idx, session_id: sid})`
6. Check if all segments `ready` or `dead` → set session `status="ready"`

**Concurrency within a session:** Run up to 3 segment coroutines concurrently per session using an `asyncio.Semaphore(3)`. This allows pipeline parallelism (segment N+1 transcribing while segment N is synthesizing) without overwhelming the GPU.

***

## Phase 4 — API Routes (Week 3)

### `routes/yt_translate.py`

Register in `main.py` under `/yt-translate/*` prefix — same pattern as all existing routers.[^1]

**All endpoints require `get_current_user()` dependency (JWT auth).**

**`POST /yt-translate/sessions`**

Input validation:

- `youtube_url`: must match YouTube URL regex (watch?v=, youtu.be/, shorts/)
- `target_language`: must be a BCP-47 code supported by at least one edge-tts voice
- `voice_id`: must exist in voice registry for target_language
- `source_language`: optional; null triggers auto-detect

Processing:

1. Call `yt-dlp --dump-json --no-download {url}` to extract metadata (title, duration, thumbnail) without downloading
2. Check `video_duration <= settings.YT_MAX_DURATION_MINUTES * 60 * 1000` — return `422` if exceeded
3. Check user's daily token budget via `token_counter.py` — estimate based on `video_duration * avg_words_per_second * avg_tokens_per_word * 1.5 (translation overhead)`; return `402` if insufficient
4. Create `YTTranslationSession` in DB
5. Return `{session_id, video_title, video_duration_ms, thumbnail_url, estimated_segments, estimated_first_segment_ready_s}`

**`POST /yt-translate/sessions/{id}/start`**

1. Validate session ownership (user_id check)
2. Validate `status == "pending"` (idempotency guard)
3. Create `BackgroundJob` record (`jobType="YT_TRANSLATION"`, `referenceId=session_id`)
4. Notify worker queue via existing `_job_queue.notify()` pattern[^1]
5. Return `{job_id, session_id, status: "queued"}`

**`GET /yt-translate/sessions/{id}/manifest`**

1. Read `yt:{session_id}:manifest` from Redis (fast path — sub-1ms)
2. If not in Redis (cold start): build from DB query, write to Redis
3. Return manifest JSON — this is the primary endpoint the frontend polls

**`GET /yt-translate/sessions/{id}/segments/{idx}`**

1. Validate ownership
2. Check `YTTranslationSegment.status == "ready"` — return `202 Accepted` with `{status: "processing", estimated_ready_s: N}` if not ready
3. Stream audio file via `FileResponse` with correct MIME type (`audio/mpeg`)
4. Set `Cache-Control: max-age=86400` — segments are immutable once generated

**`GET /yt-translate/sessions/{id}/transcript`**

Returns full `{segments: [{index, start_ms, end_ms, original_text, translated_text, word_timestamps}]}` — used for SRT/VTT export and subtitle rendering.

**`DELETE /yt-translate/sessions/{id}`**

1. Cancel any in-progress `BackgroundJob` for this session
2. Delete all audio files in `data/output/yt_translation/{session_id}/`
3. Delete all Redis keys matching `yt:{session_id}:*`
4. Delete `YTTranslationSegment` and `YTTranslationSession` records via Prisma cascade

**`GET /yt-translate/voices/{language}`**

Calls `voice_registry.list_for_language(language)` → returns `List[VoiceInfo]`. No auth required (public endpoint).

***

## Phase 5 — Frontend (Week 4)

### 5.1 StudioPanel Integration

Add "YT Translate" as a new tab in `StudioPanel.jsx`  alongside Quiz, Podcast, Explainer. Tab renders `YTTranslatorDialog.jsx` when active.[^1]

### 5.2 `YTTranslatorDialog.jsx`

**Step 1 — URL Input:**

- YouTube URL text field with paste detection
- On valid URL paste: call YouTube oEmbed API (`https://www.youtube.com/oembed?url={url}&format=json`) directly from frontend — no backend call needed for thumbnail/title preview
- Show video thumbnail, title, duration
- If duration > 2 hours: show warning "Videos over 2 hours may take significant processing time"

**Step 2 — Language Config:**

- "Detect source language automatically" checkbox (default checked)
- Source language override dropdown (BCP-47 language list) — visible only when checkbox unchecked
- Target language dropdown — on change, fetch `GET /yt-translate/voices/{language}` to populate voice picker
- Voice picker: grouped by gender, shows voice name + sample flag

**Step 3 — Submit:**

- Call `POST /yt-translate/sessions` → get `session_id`
- Call `POST /yt-translate/sessions/{id}/start`
- Navigate to `YTTranslatorPlayer.jsx` with `session_id` as prop
- Show "Preparing first segment (~10 seconds)..." loading state


### 5.3 `YTTranslatorPlayer.jsx`

**Layout: Two-pane**

- Left (60%): YouTube iframe embed
- Right (40%): Subtitle display + controls

**YouTube iframe configuration:**

- `enablejsapi=1`, `mute=1`, `autoplay=0`, `controls=1`
- Load YouTube IFrame API via `<script>` tag injection on component mount
- `onStateChange` handler fires continuously with `player.getCurrentTime()` and `player.getPlayerState()`

**Seek bar overlay:**

- Custom seek bar rendered over YouTube's native one (or alongside it)
- Colors each segment zone: green (ready), yellow (processing), grey (pending)
- Data source: manifest from `GET /yt-translate/sessions/{id}/manifest`, polled every 3 seconds until all segments ready, then polling stops

**Audio engine (Web Audio API):**

- Single `AudioContext` instance, created on first user interaction (browser autoplay policy)
- `segment_buffer_map: Map<segmentIndex, AudioBuffer>` — decoded audio ready to play
- **Buffer strategy**: maintain a look-ahead window of 3 segments ahead of `currentSegmentIdx`; fetch next segment as soon as current one starts playing
- `AudioBufferSourceNode.start(audioContext.currentTime + preciseOffset)` — `preciseOffset` computed as `(segment.startMs / 1000) - player.getCurrentTime()` at scheduling time
- `syncDeltaMs` compensation: if segment has non-zero `syncDeltaMs`, add equivalent silence buffer before next segment's scheduled start

**Subtitle display:**

- Word-level highlight using `word_timestamps` from manifest
- Current word highlighted in primary color; previous words greyed; upcoming words dimmed
- Smooth scroll to keep active word in viewport center

**Controls row:**

- Play/Pause: calls `player.playVideo()` / `player.pauseVideo()` on iframe + `audioContext.suspend()` / `audioContext.resume()`
- Speed: `player.setPlaybackRate(speed)` + `audioContext.playbackRate.value = speed` (Web Audio API `AudioBufferSourceNode.playbackRate`)
- Download Transcript: calls `GET /yt-translate/sessions/{id}/transcript` → generate SRT file client-side from word_timestamps → trigger browser download
- Language badge showing active `VoiceInfo.display_name`


### 5.4 `useYTTranslationSync.js`

Custom hook encapsulating all sync state — mirrors `usePodcastPlayer.js`:[^1]

**State managed:**

- `currentSegmentIdx`
- `bufferedSegments: Set<number>`
- `segmentBuffers: Map<number, AudioBuffer>`
- `isBuffering: boolean`
- `manifest: ManifestData`
- `syncStatus: "synced" | "drifting" | "buffering"`

**WebSocket integration:**
Listens to the existing `ws_manager` connection  for `yt_segment_ready` events — on receipt, trigger fetch and decode of that segment into `segmentBuffers`. No separate WebSocket connection needed.[^1]

**Seek handling:**
On `player.seekTo()` event from YouTube IFrame API:

1. Determine new `targetSegmentIdx` from manifest `startMs`/`endMs` ranges
2. Check if `segmentBuffers.has(targetSegmentIdx)` — if yes, schedule immediately
3. If no: show buffering state, send `{event: "seek", position_ms: N}` to backend via WebSocket to reprioritize queue, poll until segment ready

### 5.5 `src/api/yt_translate.js`

Thin fetch wrappers for all 7 endpoints following the exact same pattern as `src/api/podcast.js`. No business logic — just URL construction, auth header injection, and error normalization.[^1]

***

## Cross-Cutting Concerns

### Audit \& Token Tracking

- Every `translation_service.translate_segment()` call logged via `audit_logger.py` with endpoint tag `yt_translate`, includes `input_tokens`, `output_tokens`, `model_used`, `llm_latency_ms`[^1]
- Pass 1 glossary extraction logged separately with tag `yt_translate_glossary`
- Both count against `token_counter.py` daily budget[^1]


### Rate Limiting

- Session creation rate-limited per user: max 3 concurrent active sessions (checked in `POST /sessions` before DB write)
- Worker-level: YT_TRANSLATION jobs compete fairly with existing job types under the existing `MAX_CONCURRENT_JOBS=5` semaphore[^1]


### Model Pre-warming

In `main.py` lifespan startup sequence, add after existing warm-ups:[^1]

- Load Silero-VAD model into memory (once, module-level singleton)
- Load WhisperX model and English alignment model (most common — other languages load on first use and are cached)
- Dummy call to force ONNX/PyTorch JIT compilation


### Cleanup Policy

Background task running nightly (add to worker loop schedule):

- Delete session audio files older than 7 days
- Delete `downloading` sessions older than 1 hour (stale download detection)
- Delete `dead` sessions with all segments failed after 24 hours

***

## Full New File Inventory

```
backend/app/
├── routes/
│   └── yt_translate.py                    # NEW — 7 endpoints
├── prompts/
│   ├── yt_translation_prompt.txt          # NEW — per-segment translation
│   └── yt_glossary_prompt.txt             # NEW — Pass 1 glossary extraction
└── services/
    ├── tts_provider/                      # NEW DIRECTORY
    │   ├── base.py
    │   ├── factory.py
    │   ├── schemas.py
    │   ├── voice_registry.py
    │   ├── providers/
    │   │   └── edge_tts.py
    │   └── alignment/
    │       ├── forced_aligner.py
    │       └── alignment_schemas.py
    └── yt_translation/                    # NEW DIRECTORY
        ├── pipeline.py
        ├── segment_splitter.py
        ├── transcript_resolver.py
        ├── translation_service.py
        ├── tts_synthesizer.py
        ├── timing_adjuster.py
        └── segment_cache.py

frontend/src/
├── api/
│   └── yt_translate.js                   # NEW
├── components/
│   ├── YTTranslatorDialog.jsx             # NEW
│   └── YTTranslatorPlayer.jsx             # NEW
└── hooks/
    └── useYTTranslationSync.js            # NEW
```

**Modified files** (minimal, additive changes only):

- `main.py` — router registration, model pre-warm additions, output dir additions
- `core/config.py` — new settings group
- `worker.py` — one new job type dispatch case
- `prisma/schema.prisma` — two new models
- `StudioPanel.jsx` — one new tab entry

***

## New Dependencies

| Package | Purpose | Install |
| :-- | :-- | :-- |
| `whisperx` | CTC forced alignment for word timestamps | `pip install whisperx` |
| `pyrubberband` | WSOLA time-stretching | `pip install pyrubberband` + `apt install rubberband-cli` |
| `silero-vad` (via torch.hub) | Voice activity detection | `pip install torch` (already present) |
| `soundfile` | Audio byte conversion for pyrubberband | `pip install soundfile` |
| `librosa` | Audio loading and analysis | `pip install librosa` |

<div align="center">⁂</div>

[^1]: docs.md

