Implement an "Explainer Video Generator" feature for KeplerLab AI Notebook that creates narrated videos from PowerPoint presentations.

## Core Requirements

1. **Dual Language Selection**
   - User selects PPT content language (en, hi, gu, es, fr, de, ta, te, mr, bn)
   - User selects voice narration language (can be different from PPT)
   - User selects voice gender (male/female)

2. **Smart PPT Reuse Logic**
   - Check if PPT already exists for selected materials
   - If none found → auto-create new PPT
   - If one found → show preview with "Use this" or "Create new" options
   - If multiple found → show grid with thumbnails, let user select or create new

3. **Video Generation Pipeline**
   - Generate teaching script per slide using LLM (in narration language)
   - Generate audio using EdgeTTS (FREE, multilingual)
   - Compose video: slide PNG + audio → MP4 (1080p)
   - Concatenate all slides into final video
   - Track progress: pending → generating_script → generating_audio → composing_video → completed

## Technical Stack

**Backend (FastAPI):**
- Routes: `backend/app/routes/explainer.py`
- Services: `backend/app/services/explainer/` (script_generator.py, tts.py, video_composer.py, processor.py)
- TTS: Use `edge-tts` library (pip install edge-tts)
- Video: Use `ffmpeg` via subprocess
- Database: Add ExplainerVideo model to Prisma schema

**Frontend (React):**
- Component: `frontend/src/components/ExplainerDialog.jsx`
- API: `frontend/src/api/explainer.js`
- Features: Language selector with flags, progress bar, video player

## API Endpoints

```
POST /explainer/check-presentations
Body: { material_ids: [], notebook_id: "" }
Response: { found: bool, presentations: [{id, title, slide_count, preview_images}] }

POST /explainer/generate
Body: { material_ids, ppt_language, narration_language, voice_gender, presentation_id?, create_new_ppt: bool }
Response: { explainer_id, status, estimated_time_minutes }

GET /explainer/{id}/status
Response: { status, progress, video_url?, chapters? }

GET /explainer/{id}/video
Response: MP4 file download
```

## Database Schema (Prisma)

```prisma
model ExplainerVideo {
  id                String   @id @default(uuid())
  userId            String
  presentationId    String
  pptLanguage       String
  narrationLanguage String
  voiceGender       String
  voiceId           String
  status            String
  script            Json
  audioFiles        Json?
  videoUrl          String?
  duration          Int?
  chapters          Json?
  error             String?
  createdAt         DateTime @default(now())
  completedAt       DateTime?
  user              User     @relation(fields: [userId], references: [id])
  presentation      GeneratedContent @relation(fields: [presentationId], references: [id], onDelete: Cascade)
  @@index([userId, status])
}

// Update GeneratedContent model:
model GeneratedContent {
  // ... existing fields
  language        String?  // Add this
  materialIds     String[] // Add this
  explainerVideos ExplainerVideo[]
}
```

## EdgeTTS Voice IDs

```python
EDGE_TTS_VOICES = {
    "en": {"male": "en-US-GuyNeural", "female": "en-US-JennyNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "gu": {"male": "gu-IN-NiranjanNeural", "female": "gu-IN-DhwaniNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "ta": {"male": "ta-IN-ValluvarNeural", "female": "ta-IN-PallaviNeural"},
    "te": {"male": "te-IN-MohanNeural", "female": "te-IN-ShrutiNeural"},
    "mr": {"male": "mr-IN-ManoharNeural", "female": "mr-IN-AarohiNeural"},
    "bn": {"male": "bn-IN-BashkarNeural", "female": "bn-IN-TanishaaNeural"}
}
```

## Script Generation Prompt Template

```
You are an expert teacher creating a video explanation for a presentation slide.

SLIDE {slide_number}/{total_slides}:
Title: {slide.title}
Bullets: {slide.bullets}
Notes: {slide.notes}

Generate a detailed {narration_language} explanation (120-150 seconds of speech):
- Start with natural introduction connecting to previous slide
- Explain each bullet point with examples
- Use conversational teaching tone
- End with smooth transition to next slide

Target: ~250 words (2 minutes at conversational pace)
```

## FFmpeg Video Composition

```bash
# Per slide: Image + Audio → Video
ffmpeg -loop 1 -i slide.png -i audio.mp3 \
  -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
  -pix_fmt yuv420p -shortest \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black" \
  output.mp4

# Concatenate all slides
ffmpeg -f concat -safe 0 -i concat.txt -c copy final.mp4
```

## Key Implementation Notes

1. **PPT Reuse**: Query GeneratedContent where contentType='presentation' AND materialIds contains all requested IDs
2. **Background Job**: Use existing BackgroundJob worker system, add to queue
3. **Progress Updates**: Update ExplainerVideo.status at each pipeline stage
4. **Error Handling**: Catch exceptions, save to ExplainerVideo.error field
5. **File Paths**: Save to `data/output/explainers/{explainer_id}/`
6. **Audio Duration**: Use pydub to get MP3 duration for video timing
7. **Chapters**: Build timestamp array as you concatenate videos

## Frontend Flow

1. User clicks "Generate Explainer" in StudioPanel
2. Show ExplainerDialog modal
3. Check existing PPTs → show selection or auto-proceed
4. Show language configurator (2 separate selectors + voice gender)
5. Display info box if languages differ
6. On generate → show progress bar polling status every 2 seconds
7. On complete → show video player with download button

## Success Criteria

- ✅ User can generate explainer from existing or new PPT
- ✅ Dual language selection works correctly
- ✅ EdgeTTS generates clear audio in selected language
- ✅ Video syncs slide images with audio perfectly
- ✅ Progress tracking shows real-time status
- ✅ Final MP4 downloadable with chapter markers
- ✅ No external paid APIs used (100% free)

Start with database schema migration, then backend routes, then background processor, then frontend UI. Follow existing code patterns from podcast generation service.