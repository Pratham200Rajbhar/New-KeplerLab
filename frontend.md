# KeplerLab Frontend — Complete Architecture Reference

> Generated: 2026-03-01  
> Stack: React 19 · Vite 7 · Tailwind CSS 3 · React Router 7 · No external state library

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Directory Structure](#2-directory-structure)
3. [Component Hierarchy](#3-component-hierarchy)
4. [Routing Strategy & Protected Routes](#4-routing-strategy--protected-routes)
5. [State Management Architecture](#5-state-management-architecture)
6. [API Integration Layer](#6-api-integration-layer)
7. [Authentication Flow](#7-authentication-flow)
8. [WebSocket Layer](#8-websocket-layer)
9. [UI Component Library & Design Token Conventions](#9-ui-component-library--design-token-conventions)
10. [Theme System](#10-theme-system)
11. [Form Handling & Validation](#11-form-handling--validation)
12. [Error Boundaries & Fallback UI](#12-error-boundaries--fallback-ui)
13. [Performance Optimizations](#13-performance-optimizations)
14. [Asset Management](#14-asset-management)
15. [Build Configuration](#15-build-configuration)
16. [Environment Variables](#16-environment-variables)
17. [Deployment & Docker](#17-deployment--docker)
18. [Linting & Code Conventions](#18-linting--code-conventions)
19. [Testing Approach](#19-testing-approach)
20. [Feature Modules In Detail](#20-feature-modules-in-detail)
21. [Known Limitations & TODOs](#21-known-limitations--todos)
22. [Visual UI Reference — Component-by-Component](#22-visual-ui-reference--component-by-component)

---

## 1. Project Overview

KeplerLab is a browser-based AI-powered learning notebook. Users upload documents, YouTube links, or web content into **notebooks**, then interact with an AI assistant to generate study aids: chat, flashcards, quizzes, presentations, mind maps, explainer videos, and AI-generated podcast episodes.

The frontend is a **single-page application (SPA)** that communicates with a FastAPI backend at `VITE_API_BASE_URL` (default `http://localhost:8000`). There is no server-side rendering.

Key characteristics:
- React 19 with concurrent features
- No Redux, MobX, or Zustand — all state lives in **React Context + `useState`**
- Every API call is a plain `fetch` wrapped in a thin `apiFetch` utility; no React Query / SWR
- Streaming AI responses use **Server-Sent Events (SSE)** parsed from `ReadableStream`
- Real-time material processing uses a **WebSocket** connection (token authenticated via first message, not URL param)
- Dark/light theme toggled at runtime via Tailwind's `darkMode: 'class'` strategy; preference persisted in `localStorage`

---

## 2. Directory Structure

```
frontend/
├── index.html                  # SPA shell; FOUC-prevention inline script; Google Fonts preload
├── package.json
├── vite.config.js              # Minimal — only @vitejs/plugin-react
├── tailwind.config.js          # Full design-token extension
├── postcss.config.js           # autoprefixer
├── eslint.config.js            # Flat config (ESLint 9)
├── nginx.conf                  # Production nginx for Docker
├── Dockerfile                  # Multi-stage: node:18-alpine → nginx:alpine
└── src/
    ├── main.jsx                # ReactDOM.createRoot entry
    ├── App.jsx                 # Router, provider tree, route definitions
    ├── index.css               # Tailwind directives + full CSS custom-property design system
    ├── api/                    # Pure fetch functions (no component coupling)
    │   ├── config.js           # apiFetch, apiJson, apiFetchFormData, fetchAudioObjectUrl
    │   ├── auth.js             # login, signup, logout, getCurrentUser, refreshToken
    │   ├── chat.js             # streamChat, sendChatMessage, sessions, suggestions, SSE helpers
    │   ├── agent.js            # listGeneratedFiles, getDownloadUrl, downloadGeneratedFile
    │   ├── generation.js       # generateFlashcards, generateQuiz, generatePresentation
    │   ├── materials.js        # uploadMaterial, uploadBatch, uploadUrl, validateFiles
    │   ├── notebooks.js        # CRUD notebooks, saveGeneratedContent, getGeneratedContent
    │   ├── jobs.js             # getJobStatus, getModelsStatus, reloadModels, streamAnalysis
    │   ├── mindmap.js          # generateMindMap, getMindMap, deleteMindMap
    │   ├── podcast.js          # full podcast session CRUD + Q&A + bookmarks + export
    │   └── explainer.js        # checkExplainerPresentations, generateExplainer, getExplainerStatus
    ├── context/                # Global state via React Context
    │   ├── AppContext.jsx       # Notebook/material/chat/generated-content/UI state
    │   ├── AuthContext.jsx      # User, access token, login/logout/signup, silent refresh
    │   ├── ThemeContext.jsx     # Dark/light switching, localStorage persistence
    │   └── PodcastContext.jsx   # All podcast session, playback, and generation state
    ├── hooks/                  # Reusable stateful logic
    │   ├── useMaterialUpdates.js   # WebSocket for real-time material processing events
    │   ├── useMicInput.js          # MediaRecorder + Web Speech API for microphone
    │   ├── useMindMap.js           # Mind map check-or-generate lifecycle
    │   ├── usePodcastPlayer.js     # Segment-level audio playback with lookahead prefetch
    │   └── usePodcastWebSocket.js  # Routes podcast WS events into PodcastContext
    ├── components/             # UI components (no sub-routing inside components)
    │   ├── AuthPage.jsx        # Tab switcher between Login and Signup
    │   ├── Login.jsx           # Email/password login form
    │   ├── Signup.jsx          # Registration form
    │   ├── HomePage.jsx        # Notebook grid dashboard
    │   ├── Header.jsx          # App bar: logo, notebook name, theme toggle, user menu
    │   ├── Sidebar.jsx         # Resizable materials/sources panel (~653 lines)
    │   ├── ChatPanel.jsx       # Primary AI chat panel with SSE streaming (~1321 lines)
    │   ├── StudioPanel.jsx     # Studio grid (flashcards/quiz/ppt/podcast/explainer/mindmap) (~1883 lines)
    │   ├── ChatMessage.jsx     # Markdown rendering, code highlighting, KaTeX, block actions
    │   ├── ErrorBoundary.jsx   # Global + panel-level class component error boundaries
    │   ├── Modal.jsx           # Generic portal modal
    │   ├── FeatureCard.jsx     # Studio grid card component
    │   ├── FileViewerPage.jsx  # Public (no-auth) route for file viewing
    │   ├── UploadDialog.jsx    # Multi-mode upload: file, URL, text, YouTube
    │   ├── WebSearchDialog.jsx # Web search to material conversion
    │   ├── SourceItem.jsx      # Individual material row in sidebar
    │   ├── MindMapView.jsx     # Container for mind map hook + canvas
    │   ├── MindMapCanvas.jsx   # @xyflow/react canvas with dagre layout
    │   ├── MindMapNode.jsx     # Custom React Flow node
    │   ├── PresentationView.jsx    # Iframe-based HTML presentation viewer
    │   ├── ExplainerDialog.jsx     # Explainer video generation and polling
    │   ├── chat/               # Chat-specific sub-components
    │   │   ├── slashCommands.js        # SLASH_COMMANDS definitions (intent mappings)
    │   │   ├── SlashCommandDropdown.jsx
    │   │   ├── SlashCommandPills.jsx
    │   │   ├── CommandBadge.jsx
    │   │   ├── SuggestionDropdown.jsx
    │   │   ├── AgentThinkingBar.jsx
    │   │   ├── AgentActionBlock.jsx
    │   │   ├── AgentStepsPanel.jsx
    │   │   ├── ResearchProgress.jsx
    │   │   ├── ChartRenderer.jsx
    │   │   ├── ExecutionPanel.jsx
    │   │   ├── GeneratedFileCard.jsx
    │   │   ├── BlockHoverMenu.jsx
    │   │   ├── DocumentPreview.jsx
    │   │   └── MiniBlockChat.jsx
    │   └── podcast/            # Podcast-specific sub-components
    │       ├── index.js                # Barrel re-export
    │       ├── PodcastStudio.jsx
    │       ├── PodcastConfigDialog.jsx
    │       ├── PodcastModeSelector.jsx
    │       ├── PodcastGenerating.jsx
    │       ├── PodcastPlayer.jsx
    │       ├── PodcastTranscript.jsx
    │       ├── PodcastChapterBar.jsx
    │       ├── PodcastInterruptDrawer.jsx
    │       ├── PodcastMiniPlayer.jsx
    │       ├── PodcastSessionLibrary.jsx
    │       ├── PodcastExportBar.jsx
    │       ├── PodcastDoubtHistory.jsx
    │       └── VoicePicker.jsx
    └── assets/
        └── react.svg           # Only static asset (Vite logo placeholder)
```

---

## 3. Component Hierarchy

```
App                                    (BrowserRouter + ThemeProvider + AuthProvider + ErrorBoundary)
└── AppContent                         (AppProvider + Routes)
    ├── /auth → AuthPage               (no auth required)
    │   ├── Login
    │   └── Signup
    ├── / → ProtectedRoute → HomePage
    ├── /notebook/:id → ProtectedRoute → Workspace
    │   ├── Header                     (uses AuthContext, AppContext, ThemeContext)
    │   ├── PanelErrorBoundary > Sidebar
    │   │   ├── SourceItem (×N)
    │   │   ├── UploadDialog
    │   │   └── WebSearchDialog
    │   ├── PanelErrorBoundary > ChatPanel
    │   │   ├── ChatMessage (×N)
    │   │   │   ├── AgentStepsPanel
    │   │   │   ├── AgentActionBlock
    │   │   │   ├── GeneratedFileCard
    │   │   │   ├── ExecutionPanel
    │   │   │   ├── ChartRenderer
    │   │   │   └── BlockHoverMenu
    │   │   ├── AgentThinkingBar
    │   │   ├── ResearchProgress
    │   │   ├── SuggestionDropdown
    │   │   ├── SlashCommandDropdown
    │   │   ├── SlashCommandPills
    │   │   └── CommandBadge
    │   └── PanelErrorBoundary > StudioPanel  (wraps PodcastProvider internally)
    │       ├── FeatureCard (×6)
    │       ├── Flashcards inline view
    │       ├── Quiz inline view
    │       ├── PresentationView
    │       ├── ExplainerDialog
    │       ├── MindMapView → MindMapCanvas → MindMapNode (×N)
    │       └── PodcastStudio (consumes PodcastContext)
    │           ├── PodcastConfigDialog
    │           ├── PodcastModeSelector
    │           ├── PodcastGenerating
    │           ├── PodcastPlayer
    │           │   ├── PodcastTranscript
    │           │   └── PodcastChapterBar
    │           ├── PodcastInterruptDrawer
    │           ├── PodcastMiniPlayer
    │           ├── PodcastSessionLibrary
    │           ├── PodcastExportBar
    │           ├── PodcastDoubtHistory
    │           └── VoicePicker
    └── /view → FileViewerPage          (public, no auth)
```

**Key scoping rules:**
- `AppProvider` is placed _inside_ `Routes` so it initialises fresh state when the user navigates back from a notebook.
- `PodcastProvider` is mounted by `StudioPanel` rather than at the app root — podcast state is intentionally scoped to the studio lifecycle.
- `ThemeProvider` and `AuthProvider` are both above `AppProvider` because theme and auth must survive route transitions.

---

## 4. Routing Strategy & Protected Routes

### Router

`BrowserRouter` (HTML5 history) from `react-router-dom` v7.

### Route Table

| Path | Component | Auth Required | Notes |
|------|-----------|---------------|-------|
| `/auth` | `AuthPage` | No | Renders Login or Signup; redirects to `/` after success |
| `/` | `HomePage` | Yes | Notebook grid dashboard |
| `/notebook/:id` | `Workspace` | Yes | `:id` is a UUID or the string `"draft"` |
| `/view` | `FileViewerPage` | No | Query-param based public viewer |
| `*` (catch-all) | `<Navigate to="/" />` | — | Silent redirect |

### ProtectedRoute Implementation

```jsx
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner />;        // session initialising
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  return children;
}
```

`isLoading` is `true` while `AuthContext` is attempting a silent cookie-based refresh at mount-time. This prevents a race where unauthenticated flash occurs before the refresh completes.

### Draft Route Convention

`/notebook/draft` is a special route used before a notebook has been persisted. `Workspace` detects `id === 'draft'` and sets `draftMode: true` in `AppContext`. When the backend eventually returns a real ID (e.g., after first file upload that triggers auto-create), the component calls `navigate('/notebook/<realId>')`.

---

## 5. State Management Architecture

State is divided into three layers: **global contexts**, **local component state**, and **server state** (no caching layer - all calls go straight to the API).

### Global Contexts

#### `AppContext` (AppProvider)

The primary domain store. Lives inside `Routes` so it resets on certain navigations.

| Slice | Type | Description |
|-------|------|-------------|
| `currentNotebook` | `object \| null` | `{ id, name, isDraft? }` |
| `draftMode` | `boolean` | True while in the draft pre-persist state |
| `currentMaterial` | `object \| null` | The focused/active material |
| `materials` | `array` | All materials for the current notebook |
| `selectedSources` | `Set<string>` | IDs of checkbox-checked materials |
| `sessionId` | `string \| null` | Active chat session UUID |
| `messages` | `array` | Chat message objects: `{ id, role, content, citations, slashCommand, timestamp }` |
| `flashcards` | `object \| null` | Generated flashcard data |
| `quiz` | `object \| null` | Generated quiz data |
| `notes` | `array` | User notes (local only) |
| `pendingChatMessage` | `string \| null` | Mind-map → chat bridge: injected message |
| `loading` | `Record<string, boolean>` | Keyed loading flags, e.g. `loading['chat']` |
| `error` | `string \| null` | Global error string |
| `activePanel` | `string` | Currently visible studio panel identifier |

All state and actions are memoised with `useMemo` to avoid unnecessary re-renders. The `value` object is reconstructed only when one of its listed deps changes.

**Notebook switch side-effect:** A `useEffect` on `currentNotebook?.id` clears all per-notebook slices (materials, messages, session, generated content) when the notebook changes. It deliberately skips the initial mount (`prevId === undefined`) so `ChatPanel` can restore history from the API.

**Podcast WS bridge:** A module-level ref `_podcastWsHandlerRef` is placed inside `AppContext.value` as `podcastWsHandlerRef`. `Sidebar` writes the WS message handler into this ref; `usePodcastWebSocket` reads from it. This avoids prop-drilling across `Sidebar → AppContext → StudioPanel → PodcastContext`.

#### `AuthContext` (AuthProvider)

| Slice | Type | Description |
|-------|------|-------------|
| `user` | `object \| null` | `{ id, email, username, ... }` |
| `accessToken` | `string \| null` | JWT stored only in React state (never localStorage) |
| `isAuthenticated` | `boolean` | Derived: `!!user` |
| `isLoading` | `boolean` | True during initial silent refresh |
| `error` | `string \| null` | Login/signup error message |

Token lifecycle actions: `login`, `signup`, `logout`.

A `useRef` (`accessTokenRef`) mirrors the current access token to avoid stale closures in `logout` (which runs as an event handler callback, potentially capturing an old closure value).

An `isInitializingRef` prevents duplicate concurrent `initAuth` calls in React Strict Mode's double-invoke.

#### `ThemeContext` (ThemeProvider)

| Value | Type | Description |
|-------|------|-------------|
| `theme` | `"dark" \| "light"` | Current theme identifier |
| `isDark` | `boolean` | Convenience boolean |
| `toggleTheme()` | function | Flip current theme |
| `setTheme(t)` | function | Set to a specific value |

Persisted in `localStorage` under the key `"kepler-theme"`. Applied by toggling the `dark` class on `document.documentElement` (Tailwind's class strategy). An inline script in `index.html` reads the same key and applies the class _synchronously before first paint_ to prevent flash of unstyled content (FOUC).

#### `PodcastContext` (PodcastProvider — mounted by StudioPanel)

Dedicated context for the podcast feature (~484 lines). Contains:
- Session/sessions/segments/chapters/doubts/bookmarks/annotations state
- Playback state: `currentSegmentIndex`, `isPlaying`, `playbackSpeed`, `currentTime`, `totalElapsed`
- UI phase: `'idle' | 'generating' | 'player'`
- An `audioRef` (a stable `new Audio()` instance) shared across the context
- A `Map`-based `audioCacheRef` that stores `blob:` URLs for fetched audio segments; revoked on notebook change
- WebSocket event handler `handleWsEvent` consumed by `usePodcastWebSocket`
- Full action surface: `createSession`, `loadSession`, `startGeneration`, `playSegment`, `pause`, `resume`, `nextSegment`, `prevSegment`, `changeSpeed`, `prefetchSegment`, `submitQuestion`, `toggleBookmark`, `exportSession`, etc.

Resets completely on `currentNotebook?.id` change, revoking cached blob URLs to prevent memory leaks.

### Local Component State

Each component owns state that does not need to be shared:
- Form field values (email, password, editName, etc.)
- Modal open/close flags
- Sidebar resize width
- Active menu popovers / toast notifications
- Inline view mode (which studio tab is foregrounded)
- Chat draft message text and slash-command parse result
- Drag-active state for file drop zones
- SSE streaming in-progress flags

### Server State

There is **no caching layer** (no React Query, SWR, etc.). Every data-fetch is triggered by a `useEffect` or a user action and results go directly into component/context state. Consequences:

- No automatic background revalidation
- Data may be stale when returning to a previously visited notebook (mitigated by clearing state on notebook switch)
- No optimistic updates — mutations always wait for an API confirmation before updating local state

---

## 6. API Integration Layer

### `src/api/config.js` — The Core HTTP Utilities

**Base URL:** resolved from `import.meta.env.VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.

Three exported fetch variants:

| Function | Use case |
|----------|----------|
| `apiFetch(endpoint, options)` | Any request returning a raw `Response` (SSE streams, binary blobs) |
| `apiJson(endpoint, options)` | Shorthand for `apiFetch` + `.json()`, returns parsed object directly; handles `204 No Content` |
| `apiFetchFormData(endpoint, formData)` | File uploads — omits `Content-Type` so the browser sets the multipart boundary automatically |

**Access-token management:** The token is held in a module-level variable `_accessToken` (not in component state, not in localStorage). `AuthContext` calls `setAccessToken()` whenever the token changes, keeping the API layer in sync without creating a React state dependency.

**Automatic silent refresh on 401:**

```
Request → 401 → _refreshTokenOnce() [mutex] → retry with new token
                                              → if refresh fails → redirect to /auth
```

A single `_refreshPromise` acts as a mutex to prevent race conditions when multiple concurrent requests all receive 401 simultaneously. Only one refresh call is ever in-flight at a time; all concurrent callers share the same promise.

**Audio files:** `fetchAudioObjectUrl(path)` authenticates the request (podcast audio is gated), streams the response as a `Blob`, and returns a `blob:` URL. The caller is responsible for calling `URL.revokeObjectURL()` when done.

### API Modules Overview

| Module | Endpoints covered |
|--------|------------------|
| `auth.js` | `/auth/login`, `/auth/signup`, `/auth/logout`, `/auth/me`, `/auth/refresh` |
| `chat.js` | `/chat` (SSE stream + non-stream), `/chat/history/:id`, `/chat/sessions`, `/chat/block-followup`, `/chat/suggestions`, `/agent/research`, `/agent/execute` |
| `agent.js` | `/agent/files`, `/auth/file-token` (for signed download URLs) |
| `generation.js` | `/flashcard`, `/quiz`, `/presentation` |
| `materials.js` | `/upload`, `/upload/batch`, `/upload/url`, `/upload/text`, `/search/web`, `/materials/:id` (CRUD) |
| `notebooks.js` | `/notebooks` (CRUD), `/notebooks/:id/content` (generated content CRUD) |
| `jobs.js` | `/jobs/:id`, `/models/status`, `/models/reload`, `/agent/analyze` (SSE) |
| `mindmap.js` | `/mindmap` (POST), `/mindmap/:id` (GET/DELETE) |
| `podcast.js` | `/podcast/session` (CRUD), `/podcast/sessions/:notebookId`, `/podcast/session/:id/start`, `/podcast/session/:id/question`, doubts, bookmarks, annotations, export, summary |
| `explainer.js` | `/explainer/check-presentations`, `/explainer/generate`, `/explainer/:id/status`, `/explainer/:id/video` |

### SSE Streaming Pattern

`ChatPanel.jsx` contains a shared `readSSEStream` helper function:

```js
async function readSSEStream(response, callbacks = {}) {
  // Reads response.body as a ReadableStream
  // Parses "event: <name>\ndata: <json>\n\n" blocks
  // Dispatches to callbacks[eventName](payload)
}
```

SSE event taxonomy for chat and agent streams:

| Event | Payload |
|-------|---------|
| `start` | `{ session_id }` |
| `step` | `{ step, title, content }` — agent thinking step |
| `token` | `{ token }` — next streaming text token |
| `meta` | `{ citations, session_id, intent, ... }` |
| `done` | `{}` — stream complete |
| `error` | `{ message }` |

All streaming requests accept an `AbortSignal` for cancellation (passed as `{ signal }` to `apiFetch`).

### Client-Side File Validation

`materials.js` exports `validateFiles(files)` which checks each file against a configurable upload limit (`_maxUploadSizeMB`, default 25 MB). Returns a structured error object `{ error_code, message, details }` or `null` if valid. This runs _before_ the network request; any API 413 validations are a secondary backstop.

---

## 7. Authentication Flow

### Token Architecture

The system uses a **dual-token pattern**:
- **Access token** (15-minute JWT): kept in React memory only (`AuthContext.accessToken`). Never written to `localStorage` or `sessionStorage`. Attached as `Authorization: Bearer <token>` on every API call.
- **Refresh token** (HttpOnly cookie): set by the backend on login; invisible to JavaScript. Used exclusively at `/auth/refresh` with `credentials: 'include'`.

### Login Flow

```
Login form submit
  → api/auth.login(email, password) [POST /auth/login, credentials: include]
  → Response: { access_token } + Set-Cookie: refresh_token (HttpOnly)
  → AuthContext stores access_token in React state
  → AuthContext.getCurrentUser(access_token) [GET /auth/me]
  → AuthContext stores user object
  → scheduleRefresh() sets a 13-minute timeout
  → navigate('/')
```

### Session Restoration (page reload)

```
AuthProvider mount
  → initAuth()
  → POST /auth/refresh [credentials: include] — uses HttpOnly cookie
  → If OK: store new access_token, fetch user, scheduleRefresh()
  → If fails: isAuthenticated = false → ProtectedRoute → redirect to /auth
```

`isLoading` remains `true` during this async check. `ProtectedRoute` renders a loading spinner rather than immediately redirecting, preventing a false "not authenticated" flash.

### Silent Token Refresh Scheduling

`scheduleRefresh()` sets a `setTimeout` for 13 minutes (the access token expires at 15, giving a 2-minute safety margin). On expiry it calls `/auth/refresh` and reschedules itself recursively. If the refresh call fails (e.g., the refresh token has expired), the user is logged out silently.

The timer ref is cleared on `AuthProvider` unmount and on explicit logout.

### Logout Flow

```
logout() called
  → POST /auth/logout [Authorization: Bearer <token>] — invalidates server-side refresh token
  → clearTimeout(refreshTimerRef)
  → setAccessToken(null)
  → setUser(null)
  → ProtectedRoute sees isAuthenticated = false → redirect to /auth
```

Logout uses `accessTokenRef.current` (a ref, not the state variable) to prevent stale closures from capturing an old token.

### File Downloads (Short-lived Token)

Binary files generated by the agent (CSV, Python scripts, etc.) require authentication. The `getDownloadUrl(fileUrl)` function:

1. `GET /auth/file-token` → short-lived token string
2. Appends `?token=<token>` to the file URL
3. Triggers browser download via an ephemeral `<a>` element

---

## 8. WebSocket Layer

Two independent WebSocket connections are used.

### Material Processing Updates (`useMaterialUpdates`)

Owned by `Sidebar`. One WS connection per authenticated session.

- **URL:** `ws(s)://<api-host>/ws/jobs/<userId>`
- **Auth:** Token is NOT placed in the URL (security: it would appear in server access logs, browser history, and proxy logs). Instead, a `{ type: 'auth', token }` message is sent as the very first message after `ws.onopen`.
- **Keepalive:** Backend sends `{ type: 'ping' }`; client responds `{ type: 'pong' }`.
- **Reconnect:** Exponential backoff: 1s, 2s, 4s, 8s … capped at 30s.
- **Events handled:** Material status changes (processing, ready, failed), which cause `Sidebar` to refresh the material list.

### Podcast WebSocket (`usePodcastWebSocket`)

The podcast WS piggybacks onto the same Sidebar WS connection surface via a ref-based bridge (`podcastWsHandlerRef` in `AppContext`). `Sidebar` writes its WS ref's message handler into `podcastWsHandlerRef`. `usePodcastWebSocket` (used inside `PodcastContext`) reads from that ref.

All messages with `type` starting with `"podcast_"` are routed to `PodcastContext.handleWsEvent()`. This architecture avoids duplicating the WS connection or creating a new one just for podcast events.

---

## 9. UI Component Library & Design Token Conventions

There is **no third-party component library** (no MUI, Ant Design, shadcn/ui, etc.). Every UI element is built from scratch using Tailwind CSS utility classes plus a CSS custom-property design system.

### Design Token Structure

Tokens are defined as CSS custom properties on `:root` (light) and `.dark` (dark) in `src/index.css`. They are also wired into Tailwind's `theme.extend` in `tailwind.config.js`, making them available as Tailwind class names.

#### Surface / Background Tokens

| CSS Variable | Tailwind Class | Purpose |
|---|---|---|
| `--surface` | `bg-surface` | App background |
| `--surface-raised` | `bg-surface-raised` | Cards, panels |
| `--surface-overlay` | `bg-surface-overlay` | Dropdowns, popovers |
| `--surface-sunken` | `bg-surface-sunken` | Code blocks, inset areas |
| `--surface-50` | `bg-surface-50` | Subtle fills |
| `--surface-100` | `bg-surface-100` | Slightly heavier fills |

#### Border Tokens

| CSS Variable | Tailwind Class |
|---|---|
| `--border` | `border-border` (default) |
| `--border-light` | `border-border-light` |
| `--border-strong` | `border-border-strong` |

#### Text Tokens

| CSS Variable | Tailwind Class |
|---|---|
| `--text-primary` | `text-text-primary` |
| `--text-secondary` | `text-text-secondary` |
| `--text-muted` | `text-text-muted` |
| `--text-inverse` | `text-text-inverse` |

#### Accent (Brand Blue)

| CSS Variable | Tailwind Class |
|---|---|
| `--accent` | `bg-accent`, `text-accent` |
| `--accent-light` | `bg-accent-light` |
| `--accent-dark` | `bg-accent-dark` |
| `--accent-subtle` | `bg-accent-subtle` |
| `--accent-muted` | `bg-accent-muted` |

Light mode accent: `#2563eb`. Dark mode accent: `#3b82f6`. Both are crisp blue — intentionally not indigo.

#### Semantic Status Tokens

`success`, `danger`, `warning`, `info` — each with `DEFAULT`, `light`, `dark`, `subtle`, `border` variants.

Hard-coded utility overrides exist for UI badge colours: `status-success: #16a34a`, `status-warning: #d97706`, `status-error: #dc2626`.

### Typography Scale

Custom font-size scale (all smaller than Tailwind defaults — designed for information-dense UI):

| Token | Size | Line Height |
|-------|------|-------------|
| `2xs` | 0.6875rem | 1rem |
| `xs` | 0.75rem | 1.125rem |
| `sm` | 0.8125rem | 1.25rem |
| `base` | 0.875rem | 1.375rem |
| `md` | 0.9375rem | 1.5rem |
| `lg` | 1.0625rem | 1.625rem |
| `xl` | 1.25rem | 1.75rem |

Body `font-size` is set at `14px` globally. This is smaller than the Tailwind `base` class — the effective base is slightly smaller than standard.

### Font Families

| Family | Usage |
|--------|-------|
| Google Sans → Inter → system-ui | `font-sans` (UI chrome) |
| JetBrains Mono → Fira Code → monospace | `font-mono` (code blocks) |

Both are loaded from Google Fonts with `<link rel="preconnect">` in `index.html`.

### Border Radius Scale

| Token | Value |
|-------|-------|
| `sm` | 0.375rem |
| `md` | 0.5rem |
| `lg` | 0.625rem |
| `xl` | 0.75rem |
| `2xl` | 1rem |
| `3xl` | 1.25rem |

### Shadow Scale

| Token | Description |
|-------|-------------|
| `shadow-panel` | Standard bordered panel |
| `shadow-elevated` | Modal, elevated card |
| `shadow-glow` | Accent glow (e.g., logo icon) |
| `shadow-glow-sm` | Subtle accent glow |
| `shadow-glass` | Legacy alias for elevated |

### Animation Utilities

Defined as Tailwind custom keyframes accessible as `animate-*` utilities:

- `animate-fade-in` / `animate-fade-out`
- `animate-fade-up`
- `animate-scale-in` / `animate-scale-out`
- `animate-slide-in-right` / `animate-slide-in-left`
- `animate-shimmer` (skeleton loading)
- `animate-pulse-subtle`
- `animate-spin-slow`
- `animate-progress` (indeterminate progress bar)

Custom easing: `ease-smooth` = `cubic-bezier(0.16, 1, 0.3, 1)` (spring-like).

### Component-Layer CSS Classes (in `index.css @layer components`)

These extend Tailwind with semantic component primitives usable directly in JSX:

| Class | Description |
|-------|-------------|
| `.glass` / `.glass-light` | Panel surface with border (legacy alias for `panel-surface`) |
| `.panel-surface` | Standard raised panel surface |
| `.btn-primary` | Blue filled button |
| `.btn-secondary` | Outlined button |
| `.btn-ghost` | Text-only button |
| `.btn-icon` | Square icon-only button |
| `.btn-danger` | Red destructive button |
| `.input` | Standard text input |
| `.badge` | Inline status badge |
| `.loading-spinner` | CSS animated loading spinner |
| `.kbd` | Keyboard shortcut display |

### Spacing Extras

| Token | Value |
|-------|-------|
| `4.5` | 1.125rem |
| `13` | 3.25rem |
| `15` | 3.75rem |
| `18` | 4.5rem |

---

## 10. Theme System

### Implementation

1. **`index.html`** — Inline script reads `localStorage.getItem('kepler-theme')` and adds/removes `dark` from `<html>` synchronously before React hydrates. Default: dark.
2. **`ThemeContext`** — Initialises from the same localStorage key. Manages the class toggle on `document.documentElement` reactively.
3. **Tailwind** — Configured with `darkMode: 'class'`. All dark-mode overrides use `.dark:*` prefixes.

### Convention

All colours are defined as CSS custom properties. Tailwind classes reference `var(--token-name)`. This means:
- Dark mode does NOT use `dark:bg-gray-900` (Tailwind static values) — it uses `bg-surface` which resolves differently per theme.
- To add a new themed colour: add to `:root` and `.dark` in `index.css`, then map in `tailwind.config.js`.

---

## 11. Form Handling & Validation

There is **no form library** (no Formik, React Hook Form, Zod, etc.). All forms are hand-rolled with controlled inputs.

### Patterns Used

1. **Controlled components:** each field has a `useState` pair: `const [email, setEmail] = useState('')`.
2. **Submit handler:** `onSubmit` receives the native event, calls `e.preventDefault()`, sets a local `isLoading` flag, calls the API, and handles success/error.
3. **Error display:** errors are rendered inline above or inside the form from the `AuthContext.error` string or a local `error` state variable.
4. **HTML5 validation attributes:** `required`, `type="email"`, `type="password"` are used as baseline browser-native validators. No custom regex validation is present.

### Login Form (`Login.jsx`)

```
[email input (required, type='email')]
[password input (required, type='password')]
[submit button → disabled while isLoading]
{error && <div class="error-banner">{error}</div>}
```

Errors surface from `AuthContext.error` set by `login()`.

### Signup Form (`Signup.jsx`)

Same pattern; also collects `username`. Error from `AuthContext.error` set by `signup()`.

### Notebook Rename (inline in `HomePage.jsx`)

A `<form onSubmit={handleRename}>` with a text input and textarea. Local `editingNotebook`, `editName`, `editDescription`, `saving` states.

### Upload Dialog (`UploadDialog.jsx`)

Multi-mode: drag-and-drop, file picker, URL input, text paste. Client-side size validation via `validateFiles()` before the API call. Error displayed as a toast.

### Chat Input (`ChatPanel.jsx`)

Not a traditional form — a `<textarea>` with `onKeyDown` for enter-to-submit. Slash command parsing is done inline on each keystroke via `parseSlashCommand(message)`. Auto-suggestions are fetched with a debounce-like guard (`partialInput.length >= 3`).

### No Schema Validation

There is no Zod / Yup schema validation layer. Backend error messages (from FastAPI's `{ detail: "..." }` response) are surfaced directly to users.

---

## 12. Error Boundaries & Fallback UI

### Global `ErrorBoundary` (class component)

Wraps the entire `AppContent` tree. On render error:
- Displays a centred fallback card with "Something went wrong"
- Shows collapsible `<details>` with `error.toString()` + `componentStack` (development aid)
- Offers "Try Again" (resets state, unmounts/remounts children) and "Reload Page" (full `window.location.reload()`) buttons
- Accepts optional `fallback` prop for custom recovery UI
- Accepts optional `message` prop for a custom descriptive string

### `PanelErrorBoundary` (functional wrapper)

Wraps each of the three main panels (`Sidebar`, `ChatPanel`, `StudioPanel`) individually. Uses `ErrorBoundary` with a specific `message` string (`"The <Panel> encountered an error."`). This means one panel crashing does not destroy sibling panels.

```jsx
<PanelErrorBoundary panelName="Chat">
  <ChatPanel />
</PanelErrorBoundary>
```

### API Error Handling

- API errors (non-2xx responses) are thrown as `Error` objects with `error.message` set to the backend `detail` string or a fallback like `"HTTP 500"`.
- Call sites catch errors locally and set local/context state error strings.
- 401 responses trigger automatic silent refresh before surfacing to the caller.
- Session expiry after a failed refresh causes `window.location.href = '/auth'` (hard redirect, not React Router navigate).

### Loading States

- `AuthContext.isLoading` — shown in `ProtectedRoute` as a full-screen spinner
- `HomePage` local `loading` state — shown as a skeleton/spinner while fetching notebooks on mount
- `AppContext.loading[key]` — individual feature loading flags (e.g., `loading['flashcards']`)
- Chat streaming: a streaming flag + `AgentThinkingBar` component while SSE is in-flight
- Podcast generation: `PodcastContext.phase === 'generating'` + `PodcastGenerating` component

---

## 13. Performance Optimizations

### No Code Splitting

There is **no `React.lazy()` or `import()` dynamic imports**. All components are bundled into a single chunk. Given the current app size, this is currently acceptable, but it means the initial JS bundle includes all feature code (flashcards, podcast, mind map, etc.) even for users who only use chat.

### Memoization

- **`useMemo`** is used in `AppContext` and `AuthContext` to stabilise the context `value` object, preventing all consumers from re-rendering on unrelated state changes.
- **`useCallback`** wraps all action functions passed through context.
- **`memo`** is used selectively: `ChatMessage` is wrapped in `React.memo` to avoid re-rendering the entire message list on new token arrivals (only the last message renders new content during streaming).
- `useMindMap` uses a `sourcesKey` string (sorted IDs joined with `,`) as a stable dep for `useMemo`/`useEffect` to avoid reacting to new array references when content is identical.

### Podcast Audio Caching

`PodcastContext` maintains an `audioCacheRef` (`Map<segmentPath, blobUrl>`). Once a segment's audio is fetched the URL is stored; subsequent plays re-use the `blob:` URL without another network request. All cached URLs are revoked via `URL.revokeObjectURL()` on notebook change to prevent memory leaks.

`usePodcastPlayer` prefetches the **next 2 segments** whenever `currentSegmentIndex` changes, by calling `prefetchSegment(idx)` which populates the cache ahead of time.

### Sidebar Resizable Panel

The sidebar has a locally managed `width` state (`useState(320)`) and a mouse-drag `isResizing` flag. Resize is debounced implicitly by the rate of `pointermove` events.

### Streaming Token Rendering

During SSE streaming, `ChatPanel` accumulates tokens into a `streamingContent` ref (to avoid setState on every token) and periodically flushes to a `streamDisplay` state using a RAF-like approach. The `sanitizeStreamingMarkdown` utility patches unclosed fences/markers so the markdown renderer never sees broken syntax mid-stream.

### Static Asset Cache Policy (nginx)

JS/CSS/image/font files get `Cache-Control: public, immutable` with a 1-year expiry. Vite's content-hash filenames make this safe. The HTML entry point gets `Cache-Control: no-cache` so browsers always check for a new build.

---

## 14. Asset Management

- **Only static asset:** `src/assets/react.svg` (Vite scaffolding leftover, not referenced in production code)
- **Fonts:** Loaded externally from Google Fonts CDN (Google Sans, Inter, JetBrains Mono). Not self-hosted. `<link rel="preconnect">` entries reduce the initial connection latency
- **Icons:** All icons are inline SVG paths in JSX — no icon library dependency (Heroicons patterns used manually)
- **Favicon:** `public/vite.svg` (Vite default; not replaced with a custom app icon — this is a known TODO)
- **KaTeX CSS:** Imported in `ChatMessage.jsx` via `import 'katex/dist/katex.min.css'` — bundled by Vite

---

## 15. Build Configuration

### Vite (`vite.config.js`)

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```

No customisation beyond the React plugin. Notable implications:
- No manual chunk splitting configuration — single output bundle
- No path aliases (no `@` → `src` shorthand; all imports use relative paths)
- No proxy configuration in `vite.config.js` — dev proxying is expected to be handled via the `VITE_API_BASE_URL` env var pointing to the backend directly, or via an external reverse proxy

### PostCSS (`postcss.config.js`)

Configured with `tailwindcss` and `autoprefixer` plugins.

### ESLint (`eslint.config.js`)

ESLint 9 flat config:
- `@eslint/js` recommended rules
- `eslint-plugin-react-hooks` — enforces Rules of Hooks
- `eslint-plugin-react-refresh` — prevents accidentally exporting non-components from modules that HMR monitors

Custom rules:
```js
'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }]  // allow UPPER_SNAKE_CASE consts
'react-refresh/only-export-components': ['warn', { allowConstantExport: true }]
'react-hooks/immutability': 'off'
'react-hooks/set-state-in-effect': 'off'
```

---

## 16. Environment Variables

All runtime configuration is injected at **build time** via Vite's `import.meta.env.*` mechanism.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | FastAPI backend base URL |
| `VITE_APP_NAME` | No | — | Application name (available at build time) |
| `VITE_APP_VERSION` | No | — | Build version string |

**Important:** There is no `.env.example` file checked into the repo (none present in the workspace). Missing env var documentation is a known gap.

**Convention:** Variables are accessed in exactly two places:
1. `src/api/config.js` — reads `VITE_API_BASE_URL` and sets the module-level `API_BASE_URL` constant
2. `src/api/podcast.js`, `src/api/agent.js` — read `VITE_API_BASE_URL` directly for constructing absolute audio/download URLs (not routed through `config.js` — an inconsistency)

There is no runtime environment variable injection (no `window.__env__` or similar). The values are baked into the JS bundle at `vite build` time.

---

## 17. Deployment & Docker

### Dockerfile (`frontend/Dockerfile`)

Multi-stage build:

**Stage 1: `build` (node:18-alpine)**
1. `COPY package*.json ./` and `npm ci --only=production`
2. `COPY . .`
3. Accepts `ARG VITE_API_BASE_URL`, `VITE_APP_NAME`, `VITE_APP_VERSION` as build arguments; sets them as `ENV` so Vite can read them during `npm run build`
4. `RUN npm run build` — outputs to `/app/dist`

Note: `npm ci --only=production` installs all listed dependencies including dev dependencies needed for the build (Vite, Tailwind, ESLint). The `--only=production` flag means it skips the `devDependencies` key, but crucially Vite and PostCSS are listed under `devDependencies` — this means the build would _fail_ with `--only=production`. This is a **bug** in the Dockerfile (see Known Limitations).

**Stage 2: `production` (nginx:alpine)**
1. Installs `curl` for health checks
2. Copies custom `nginx.conf` to `/etc/nginx/conf.d/default.conf`
3. Copies `/app/dist` to `/usr/share/nginx/html`
4. Copies and enables `docker-entrypoint.sh`
5. Exposes port 80

### nginx Configuration

- Gzip compression enabled for text/JS/CSS/SVG/font types, min 1024 bytes
- 1-year immutable cache for static hashed assets (`js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot`)
- `try_files $uri $uri/ /index.html` for client-side routing fallback (SPA mode)
- `no-cache` on the HTML entry point
- Optional API proxy: `location /api/ → http://backend:8000/` (useful in docker-compose setups)
- Security headers: `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, `Referrer-Policy`

---

## 18. Linting & Code Conventions

### File Naming
- Components: `PascalCase.jsx`
- Hooks: `camelCase.js` with `use` prefix
- API modules: `camelCase.js`
- Context files: `PascalCaseContext.jsx`

### Import Ordering (informal, not enforced)
1. React/library imports
2. Context imports
3. API imports
4. Component imports
5. Relative utility imports

### JSDoc
API functions include JSDoc `@param` and `@returns` annotations. Component files generally do not.

### Component Structure Convention
Large components (ChatPanel, StudioPanel, Sidebar) follow a pattern:
1. Imports
2. Module-level constants (icons as inline components, static arrays)
3. Helper functions (e.g., `readSSEStream`)
4. Main component function
5. `export default`

### Context Consumer Guard
All context hooks assert their context and throw clearly:
```js
if (!context) throw new Error('useApp must be used within an AppProvider');
```

---

## 19. Testing Approach

**There are no test files in the frontend workspace.** No testing framework (Jest, Vitest, Playwright, Cypress) is installed. This is a significant gap.

Implications:
- No unit tests for API helpers, context logic, or utility functions
- No integration tests for auth flows or routing
- No E2E tests for critical user paths (upload → chat, generate flashcards, etc.)
- No visual regression testing

Recommended additions:
- **Vitest** (compatible with Vite, already in the ecosystem) for unit/integration tests
- **@testing-library/react** for component tests
- **Playwright** or **Cypress** for E2E testing

---

## 20. Feature Modules In Detail

### Chat (`ChatPanel.jsx` — ~1321 lines)

The most complex component. Responsibilities:
- Loads chat history from API on notebook mount
- Manages multiple sessions (create, switch, delete) via a session selector dropdown
- Handles SSE streaming: shows `AgentThinkingBar` during reasoning, accumulates tokens, renders final message
- Supports `/slash` commands: parses on input, shows `SlashCommandDropdown`, sends `intent_override` to backend
- Shows quick-action chips for common prompts (Summarize, Explain, Key Points, Study Guide)
- Auto-suggestions: calls `/chat/suggestions` when input ≥ 3 chars, shows `SuggestionDropdown`
- Block-level interactions: per-paragraph hover menu (`BlockHoverMenu`) for ask/simplify/translate/explain
- Renders `AgentActionBlock` for agent tool calls, `ExecutionPanel` for code execution output, `ChartRenderer` for data visualizations, `GeneratedFileCard` for downloadable agent outputs
- Research mode: shows a 5-step `ResearchProgress` tracker while `/web` or `/agent` query is in flight
- `pendingChatMessage` bridge: when a node in `MindMapCanvas` is clicked, it sets `pendingChatMessage` in `AppContext`; `ChatPanel` detects the change and auto-submits it

### Studio (`StudioPanel.jsx` — ~1883 lines)

A grid of feature cards. Each card triggers a generation flow:

| Feature | Generation Pattern |
|---------|-------------------|
| Flashcards | `apiJson('/flashcard')` → response renders inline (flip-card UI) |
| Quiz | `apiJson('/quiz')` → response renders inline (MCQ UI) |
| Presentation | `apiJson('/presentation')` → HTML string → rendered in `PresentationView` iframe |
| Podcast | Full session lifecycle via `PodcastContext` + WebSocket events |
| Explainer Video | Async job: `generateExplainer()` → poll `getExplainerStatus()` until ready → `fetchExplainerVideoBlob()` |
| Mind Map | `useMindMap` hook: check-for-existing → generate if stale → render in `MindMapCanvas` |

Generated content (flashcards, quizzes, presentations) can be saved to the notebook via `saveGeneratedContent()` and retrieved on next load with `getGeneratedContent()`. Saved items are shown in a "Saved" sub-tab within each feature view.

### Mind Map (`MindMapCanvas`, `MindMapView`, `useMindMap`)

- Layout is computed with **dagre** (directed graph auto-layout)
- Rendered with **@xyflow/react** (formerly React Flow v12)
- Nodes are custom `MindMapNode` components
- Clicking a node sends the node label to `AppContext.setPendingChatMessage()`, bridging to `ChatPanel`
- Export: `html-to-image` + `jsPDF` for PNG/PDF download

### Podcast

A fully stateful multi-phase experience:
- **idle** → `PodcastSessionLibrary` (list past sessions) or create new via `PodcastConfigDialog`
- **generating** → `PodcastGenerating` (progress via WebSocket `podcast_*` events)
- **player** → `PodcastPlayer` + `PodcastTranscript` + `PodcastChapterBar`
  - Live Q&A: `PodcastInterruptDrawer` pauses playback and submits a doubt to the backend
  - Bookmarks and annotations stored server-side
  - Export: `PodcastExportBar` triggers server-side export job
  - Mini-player: `PodcastMiniPlayer` shown while browsing other studio features

Audio is fetched authenticated via `fetchAudioObjectUrl` and cached as `blob:` URLs to allow gapless segment-by-segment playback. `usePodcastPlayer` prefetches the next 2 segments ahead.

Session status constants mirror the backend enum: `created → script_generating → audio_generating → ready → playing → paused → completed → failed`.

### Sidebar

- Resizable via mouse drag (260px–600px, default 320px)
- Drag-and-drop file upload (batched)
- Per-material checkbox for multi-source chat and content generation
- Material status badges (processing, ready, failed)
- Inline text viewer (fetches raw text via `getMaterialText()`)
- Document preview via `DocumentPreview` component
- Source search / filter within the sidebar
- Web search dialog (`WebSearchDialog`) to import search results as materials

---

## 21. Known Limitations & TODOs

### Explicit TODOs in Code

| Location | TODO |
|----------|------|
| `App.jsx` → `Workspace` `loadNotebook` catch block | `// TODO: Redirect to home or show error` when notebook fetch fails |

### Implicit Gaps & Limitations

**No code splitting / lazy loading**
All components are eagerly imported. The bundle includes podcast, mind map, flashcard, explainer code even on the home page. Adding `React.lazy()` + `Suspense` for each major feature module (`StudioPanel`, `PodcastStudio`, `MindMapCanvas`) would improve initial load time.

**No caching layer / server state management**
Data-fetching results are not cached. Navigating away and back to a notebook re-fetches all materials and history. A library like TanStack Query would add stale-while-revalidate semantics, automatic background refetching, and request deduplication.

**Dockerfile bug: `npm ci --only=production`**
The build stage uses `--only=production` which skips `devDependencies`. However, `vite`, `@vitejs/plugin-react`, `tailwindcss`, `postcss`, `autoprefixer`, and ESLint plugins are all `devDependencies`. The build will fail unless changed to `npm ci` (or `npm ci --include=dev`).

**No `.env.example` file**
Environment variable requirements are undocumented outside of this file and the Dockerfile `ARG` declarations.

**Google Fonts CDN dependency**
Fonts are loaded from `fonts.googleapis.com`. This means:
- The app has a degraded font appearance with no network or behind strict firewalls
- GDPR/privacy implications for EU deployments (external font requests reveal user IP to Google)
- Recommendation: self-host fonts in `public/fonts/`

**Favicon is the Vite default**
`public/vite.svg` is used as the favicon. No branded icon has been created.

**`VITE_API_BASE_URL` read in multiple places**
`src/api/podcast.js` and `src/api/agent.js` read `import.meta.env.VITE_API_BASE_URL` directly instead of importing `apiConfig.baseUrl` from `config.js`. This is an inconsistency — if the variable name ever changes, these files won't be caught.

**No error recovery for stale `AppContext` state on navigation failure**
If `getNotebook(id)` throws in `Workspace` (404, 500, etc.), the error is only `console.error`'d; the user is stuck on the current page with no notebook loaded. The TODO comment acknowledges this.

**No form input validation library**
Login/signup forms rely on HTML5 `required` and `type="email"` attributes only. There is no frontend password-strength check, no username character validation, and no confirmation password field on signup.

**`PodcastMiniPlayer` persistence**
When a user leaves the podcast studio tab (by clicking another feature card), the `PodcastMiniPlayer` floats over the studio grid. If `StudioPanel` unmounts (navigating away from the notebook), the podcast audio will stop. There is no background audio playback across navigation.

**No testing infrastructure**
See [Section 19](#19-testing-approach). Zero test coverage.

**`activePanel` in `AppContext` is not fully wired**
`setActivePanel` exists in the context but it's unclear if all consumers use it consistently. Studio panel navigation is managed with local `activeView` state in `StudioPanel` instead.

**WebSocket authentication race on rapid session changes**
If the user logs out and back in quickly, there's a window where the old WS connection's `onclose` tries to reconnect using a stale token. The exponential backoff delay partly mitigates this but there's no explicit cancel on logout.

**No pagination for notebooks or materials**
`getNotebooks()` and `getMaterials()` return all records. At scale this will become slow. No pagination, cursor, or virtual-scroll is implemented.

**`index.html` starts with `class="dark"` hardcoded**
The inline script _updates_ the class, but the initial HTML has `class="dark"`. If the script fails (CSP, JS disabled), the site defaults to dark mode regardless of localStorage.

---

## 22. Visual UI Reference — Component-by-Component

This section describes the exact on-screen appearance of every component: size, shape, color, typography, interactive states, and animations.  All sizes are Tailwind utility values (1 unit = 4 px).

---

### 22.1 HomePage (`/`)

The home page is a standalone route (not inside the notebook shell). It has its own header and a grid of notebook cards.

#### Header bar
- Full-width `border-b border-border` strip, `px-6 py-4`.
- **Logo cluster** (left): 8×8 rounded-xl `bg-accent` box with white stacked-layers SVG (4×4) + `shadow-glow-sm` + "KeplerLab" text (`text-base font-semibold text-text-primary`).
- **Right controls**: theme toggle `btn-icon` (sun/moon 5×5 SVG) → settings `btn-ghost text-sm` (gear icon + "Settings" label) → user avatar (`w-8 h-8 rounded-xl bg-accent/20 text-accent-light text-sm font-medium hover:bg-accent/30`; shows first letter of username/email).
- **Avatar dropdown** (`animate-fade-in glass rounded-xl shadow-glass w-52`): top section `px-4 py-3 border-b` shows username (sm font-medium) + email (xs text-muted truncate); "Sign out" row with arrow-right icon, `text-sm text-text-secondary hover:bg-surface-raised`.

#### Main content
- `max-w-6xl mx-auto px-6 py-12`.
- H1: `text-4xl md:text-5xl font-light text-text-primary` — "Welcome to KeplerLab".
- Subtitle: `text-text-secondary text-lg mb-12` — "Your AI-powered research assistant".
- Section header row: "MY NOTEBOOKS" label (`text-sm font-medium text-text-muted uppercase tracking-wider`) + count badge (xs text-muted).

#### Notebook grid
- `grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4`.

**"Create new notebook" card** (first cell):
- `h-48 rounded-2xl border-2 border-dashed border-border`; hover: `border-accent/50 bg-accent/5`.
- Centered 12×12 rounded-xl `bg-accent/20` box (hover: `bg-accent/30 shadow-glow-sm`) with 6×6 `+` icon (`text-accent-light`).
- "Create new notebook" caption in `text-text-muted text-sm`.

**Existing notebook card**:
- `h-48 rounded-2xl glass cursor-pointer`; hover: `shadow-glass border-accent/30`.
- Top-left: 10×10 rounded-xl `bg-accent/15` box with open-book SVG (`text-accent-light`).
- Bottom text: notebook name (`text-text-primary font-medium text-sm truncate`) + optional description (xs text-muted) + relative date (xs text-muted opacity-60).
- **3-dot menu button**: `absolute top-3 right-3 p-1.5 rounded-lg bg-surface-overlay/80 opacity-0 group-hover:opacity-100`; shows 3 vertical dots.
- **Dropdown** (`glass-strong rounded-xl shadow-glass w-36 animate-fade-in`): "Rename" (pencil icon) + "Delete" (`text-red-400 hover:bg-red-500/10`).

**Rename modal** (`modal w-full max-w-md`): standard `modal-header` + form with two `input` fields (Name, Description) + `modal-footer` (Cancel / Save).

**Delete confirmation modal** (`max-w-sm`): centered 12×12 `rounded-full bg-red-500/10` trash icon, "Delete notebook?" heading, one-line description, Cancel + red Delete buttons.

---

### 22.2 Auth Page (`/auth`)

#### Login form
- Full-screen surface (`min-h-screen bg-surface flex items-center justify-center`).
- Card: `w-full max-w-md glass rounded-2xl p-8 shadow-glass`.
- Logo row at top: 10×10 rounded-xl `bg-accent shadow-glow` + "KeplerLab" (xl font-bold) + "Sign in to continue" (sm text-muted).
- Form fields use the `.input` class: full-width, `rounded-lg bg-surface-raised border border-border focus:border-accent focus:ring-2 ring-accent/20 text-sm`.
- "Sign in" button: `.btn-primary w-full py-2.5 text-sm`.
- "Don't have an account? Sign up" toggle link in `text-accent-light text-sm`.
- Error banner: `bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400`.

#### Sign-up form
- Same card layout; adds Username field; button reads "Create account".

---

### 22.3 App Shell — Three-Panel Layout (`/notebook/:id`)

After login, the notebook view is a full-viewport flex row:

```
[Sidebar] [ChatPanel] [StudioPanel]
  ~320px   flex-1      ~360px
```

- Root `div`: `h-screen flex flex-col overflow-hidden bg-surface`.
- **Header** is pinned at top (`h-14`); the three panels fill the remaining viewport height.

---

### 22.4 Header (`Header.jsx`)

- `h-14 glass flex items-center justify-between px-4 relative z-40`.
- **Left cluster**: optional back-chevron `btn-icon` → logo (8×8 rounded-xl `bg-accent shadow-glow-sm` with white layers SVG 4×4) → "KeplerLab" (`base font-semibold`) → `1px bg-border h-5` divider → book SVG (`text-text-muted`) → notebook name (`text-sm text-text-secondary`, max-w-[200px] truncate).
- **Right cluster**: theme toggle `btn-icon` (sun/moon 5×5 SVG), user avatar `btn-icon` (initial letter in 7×7 rounded-full `bg-accent/20 text-accent-light font-medium`).

---

### 22.5 Sidebar (`Sidebar.jsx`)

Resizable aside panel, default 320 px wide (min 260, max 600).  
Root: `flex flex-col h-full bg-surface border-r border-border`.

#### Header row
- `px-4 py-3 flex items-center justify-between`.
- "Sources" label (`text-[15px] font-semibold text-text-primary`).
- Gear icon button (`text-text-muted`).

#### "Add sources" button
- Full-width pill: `rounded-full border border-border mx-4 mb-3 py-2 flex items-center justify-center gap-1.5`.
- `+` icon + "Add sources" (`text-[14px] text-text-secondary`).

#### Premium web search box
- `rounded-[18px] bg-gradient-to-b from-surface-raised to-surface shadow-[0_4px_20px_rgba(0,0,0,0.2)] mx-4 mb-4 p-3 relative overflow-hidden`.
- Decorative glow: `absolute -top-4 -right-4 w-24 h-24 bg-blue-500/5 rounded-full blur-2xl`.
- Inside: `bg-surface/80 rounded-xl border border-border/50 flex items-center gap-2 px-3 py-2 focus-within:border-blue-500/50 focus-within:ring-[3px] focus-within:ring-blue-500/20`.
  - Blue search icon (4×4, `text-blue-400/70`).
  - Input: placeholder "Search the web for sources..." (`text-[13px] text-text-muted`).
- Bottom row: 
  - File type dropdown: `w-[160px] bg-surface/80 rounded-lg border border-border/40 px-2 py-1.5 flex items-center gap-2 text-[11.5px] text-text-secondary`; document icon on left, chevron on right.
  - "Web" button: `bg-blue-600 hover:bg-blue-500 text-white text-[12px] font-semibold px-3 py-1.5 rounded-lg shadow-lg transition-all`; globe icon.

#### "Select all sources" row
- `px-4 py-2 flex items-center justify-between`.
- "Select all sources" in `text-[14px] text-text-muted`.
- 4×4 checkbox (`rounded-[4px] border`): 
  - All checked: `border-text-primary` + white checkmark SVG;
  - Indeterminate: `border-gray-400` + dash icon;
  - Unchecked: `border-border`.

#### Materials list (scrollable)
- `flex-1 overflow-y-auto px-2 py-1`.
- Drag-active tint: `bg-accent/5`.
- Load error banner (full-width, `text-red-400 bg-red-500/10 text-xs p-3 text-center`, click-to-retry).
- **Empty state**: centered upload-cloud SVG (8×8 text-muted) + "Add sources" (`text-sm font-medium text-text-muted`) + "Upload PDFs, docs, or text files" (xs text-muted).

#### Text-preview modal
- Fixed full-screen with `bg-black/60 backdrop-blur-sm`.
- Panel: `max-w-5xl h-[85vh] bg-surface rounded-2xl border shadow-2xl flex flex-col mx-auto mt-[5vh]`.
- Header: blue-tinted document icon `w-10 h-10 rounded-xl bg-blue-500/10` + filename + "Document Preview" subtitle + X `btn-icon`.
- Blue glow overlay at top: `absolute -top-20 left-1/2 -translate-x-1/2 w-80 h-40 bg-blue-500/10 blur-3xl`.
- Body: `DocumentPreview` markdown viewer or `animate-pulse` loading spinner.

#### Resize handle
- `absolute right-0 top-0 bottom-0 w-[1.5px]`; hover: `bg-accent/30 cursor-col-resize`.

---

### 22.6 SourceItem (`SourceItem.jsx`)

Each source in the sidebar list.

- Root: `source-item group flex items-start gap-3 px-3 py-2.5 rounded-lg border border-transparent cursor-pointer`.
  - Checked state: `bg-surface-overlay`.
  - Hover (unchecked): `bg-surface-100`.

**Left icon box** (`w-8 h-8 rounded-lg border backdrop-blur-sm shadow-inner flex items-center justify-center`):

| Source type | Gradient / colors |
|---|---|
| YouTube | `from-red-500/20 to-red-600/5 border-red-500/20 text-red-500` |
| URL/web | Blue shades |
| PDF | Red shades |
| DOCX | Blue shades |
| PPTX | Orange shades |
| XLSX/CSV | Green shades |
| MP3 | Purple shades |
| MP4/video | Pink shades |
| ZIP | Amber shades |
| PNG/JPG/image | Teal shades |
| TXT | Gray shades |

- Icon pulses (`animate-pulse`) while processing; `grayscale opacity-50` when failed.

**Middle name area**:
- Filename: `text-[13px] truncate font-medium`; active → `text-white`; failed → `text-red-400 line-through`; default → `text-gray-200`.
- **Status badge** (processing / failed): animated pill `rounded-full border text-[10px]` matching type color; ping-dot for live processing; along-side: `animate-[progress]` progress bar (`max-w-[100px] h-1 bg-gray-700/50`).

**3-dot context menu** (hover only, `opacity-0 group-hover:opacity-100`):
- Trigger: `p-1.5 rounded-md hover:bg-surface-overlay`.
- Dropdown: `min-w-[160px] py-1 rounded-xl bg-surface-100 border-border-strong shadow-xl absolute right-0 top-8 z-30`.
- Items: "View text" (eye icon, text-text-secondary), "Rename" (pencil icon), "Remove source" (trash icon, `text-red-400 hover:bg-red-500/10`).

**Right checkbox** (`w-4 h-4 rounded-[4px] border flex-shrink-0`):
- Checked: `border-white bg-transparent` + white checkmark SVG.
- Unchecked: `border-border-strong hover:border-gray-400`.
- Processing: replaced by spinning color-matched SVG spinner.

---

### 22.7 ChatPanel (`ChatPanel.jsx`)

Middle column; `flex-1 flex flex-col h-full overflow-hidden`.

#### Panel header (`panel-header border-b border-border bg-surface`)
- **Left**: "Chat" (`text-sm font-semibold text-text-primary`) + optional session name pill (`text-xs bg-surface-overlay px-2 py-0.5 rounded-full max-w-[140px] truncate text-text-muted`).
- **Right**:
  - Green sources pill (`bg-status-success/10 text-status-success border border-status-success/20 text-xs px-2 py-0.5 rounded-full`): animated ping-dot + "N sources"; or blue "Indexing…" pulse if processing.
  - "History" button: clock icon + "History" text (`btn-secondary py-1.5 px-2.5 text-xs`).
  - "+" new chat icon-button: `btn-secondary p-1.5`.

#### Empty state — 3 variants
1. **Has source**: glass pill with pulse-green dot + selected source count/name; large H2 "What would you like to know?" (`text-2xl font-light`); subtext (`text-text-muted text-sm`); **4 quick-action chips** row: 📝 Summarize, 💡 Explain this, 🎯 Key points, 📚 Study guide — each a `quick-action-chip` CSS component with emoji + text.
2. **Processing**: glass box with spinning `sync` icon in `text-accent animate-spin`; "Processing your source…"; xs subtext about unlocking.
3. **No source**: glass box with book SVG; "Welcome to KeplerLab"; subtext about adding sources.

#### Messages area
- `flex-1 overflow-y-auto`. Inner `max-w-4xl mx-auto px-4 py-8`.
- Each `ChatMessage` rendered (see §22.8).
- `ResearchProgress` on active research streams.
- **Streaming bubble**: `ai-avatar` (lightbulb SVG `w-4 h-4` with `streaming-pulse` animation) + markdown content + blinking `streaming-cursor` span.
- **Typing indicator** (`typing-indicator` three-dot animation CSS) with optional step label (`text-xs text-text-muted`).

#### Sticky input area
- `sticky bottom-0 bg-gradient-to-t from-surface-100 via-surface-100 to-transparent pt-12`.
- Stacked vertically (top to bottom):
  1. **`AgentThinkingBar`** — see §22.13.
  2. **`SuggestionDropdown`** — floating autocomplete above input.
  3. **MindMap context banner** — `border-l-4 border-accent-light bg-surface-raised rounded-r-xl px-4 py-2 text-sm`; shows "Asking about: **nodeName**" + × dismiss button.
  4. **`SlashCommandPills`** — horizontal pill row of available slash commands.
  5. **`SlashCommandDropdown`** — floating menu above input.
  6. **`chat-input-container`** — `rounded-2xl shadow-elevated bg-surface-raised border border-border focus-within:ring-2 ring-accent/20`.

**chat-input-container internals**:
- Optional `CommandBadge` (left, `pl-3`).
- `textarea`: `text-[15px] min-h-[48px] max-h-[200px] py-3.5 px-4 leading-relaxed resize-none bg-transparent w-full focus:outline-none text-text-primary placeholder:text-text-muted`.
- Right button cluster:
  - ✨ Suggest: `w-9 h-9 rounded-[10px] bg-accent/10 text-accent-light hover:bg-accent/20` (only if text typed).
  - 🔬 Research: `w-9 h-9 rounded-[10px] text-text-muted disabled:opacity-30`.
  - **Stop**: `bg-red-500/20 text-red-400 rounded-[10px] w-9 h-9` (while streaming).
  - **Send**: `bg-accent text-white rounded-[10px] w-9 h-9 disabled:bg-surface-overlay disabled:text-text-muted`.

**Footer hint row** (`text-[11px] text-text-muted`):
- `<kbd>` styled pills: `px-1.5 py-0.5 rounded bg-surface-overlay border border-border font-mono text-[10px]`.
- Shows: Enter = send · ⇧Enter = new line · / = commands.
- Character counter on right (red when > 1800 chars).

#### History modal (full-screen overlay)
- Two-panel inside `Modal`: left sidebar (`w-64 border-r border-border flex flex-col bg-gradient-to-b from-surface/80 to-surface`).
- "New Chat" blue `btn-primary` at top of left sidebar.
- "Overview" stats box (`bg-surface-overlay rounded-xl p-4`): total conversation count in large bold + "Total Conversations" label.
- Sessions grouped under headers Today / Yesterday / Previous 7 Days / Older; each item: session title (`text-sm text-text-primary truncate`) + timestamp (xs text-muted) + hover × delete button.
- Right panel: search input + session list; empty state: accent-subtle rounded-2xl box + "No Conversations Yet".

#### Toast
- `fixed bottom-4 right-4 z-50 bg-surface-raised px-4 py-2 rounded-lg shadow-lg border animate-fade-in text-text-primary text-sm`.

---

### 22.8 ChatMessage (`ChatMessage.jsx`)

#### User bubble
- `chat-msg-user flex justify-end py-3`.
- Inner: `max-w-[80%] sm:max-w-[70%]`.
- Bubble: `.user-bubble` CSS class — `bg-accent/15 text-text-primary rounded-2xl rounded-br-sm px-4 py-3`.
- Optional `CommandBadge` above text (if slash command used).
- Text: `whitespace-pre-wrap text-[15px] leading-relaxed`.

#### AI message
- `chat-msg-ai group py-5 flex gap-3 w-full`.
- **Avatar** (`.ai-avatar`): 8×8 rounded-full `bg-accent/10 border border-accent/20 flex-shrink-0 mt-0.5 flex items-center justify-center`; lightbulb SVG `w-4 h-4 text-accent`.
- **Content** (`flex-1 min-w-0`):
  - `AgentActionBlock` collapsible step drawer (if `stepLog.length > 0`) — see §22.15.
  - Main content in `.markdown-content` div — see §22.9.
  - `GeneratedFileCard` row (file download chips) — see §22.16.
  - **Citations row** (`flex flex-wrap gap-1.5 mt-3`): each citation is a `.citation` chip — `bg-surface-overlay rounded-md px-2 py-0.5 text-xs` with `.citation-number` accent badge + truncated source name.
  - **Action bar** (`.ai-action-bar opacity-0 group-hover:opacity-100 transition-opacity mt-2 flex items-center gap-0.5`):
    - Copy button: icon-only `p-1.5 rounded-md`.
    - 👍 Good response button.
    - 👎 Bad response button.
  - **Tool badges row** (when tools used but no step log): `flex flex-wrap gap-1.5 mt-2.5`; each badge: `text-xs px-2 py-0.5 rounded-full bg-surface-overlay/60 border border-border/20 text-text-muted` with emoji + label.

#### Markdown renderer element styles (`.md-*`)

| Class | Appearance |
|---|---|
| `.md-heading` | font-semibold, mt-6 mb-2 text-text-primary |
| `.md-h1` | text-2xl |
| `.md-h2` | text-xl border-b border-border pb-2 |
| `.md-h3` | text-lg |
| `.md-paragraph` | text-[15px] leading-relaxed text-text-secondary mb-3 |
| `.md-blockquote` | pl-4 border-l-4 border-accent/40 italic text-text-muted ml-0 my-3 |
| `.md-link` | text-accent-light underline + external-link SVG (3×3 opacity-50) |
| `.md-inline-code` | font-mono text-[13px] bg-surface-overlay px-1.5 py-0.5 rounded border border-border/30 |
| `.md-code-block-wrapper` | rounded-xl overflow-hidden border border-border mt-3 mb-4 |
| `.md-code-header` | `flex items-center justify-between px-4 py-2 bg-surface-sunken text-xs text-text-muted` + language label + Copy button |
| `.md-table` | Full-width, `border-collapse`, `th` accent-tinted headers, alternating row bg |
| `.md-image-caption` | Centered italic xs text-muted below `<img>` |

**Code execution block** (data analysis): `ChartRenderer` renders base64 PNG inline. "Raw output" is a `<details>` collapsible showing `<pre>` output in monospace.

**Multi-source response**: separated by tool-badge headers (emoji + label in xs text-text-muted font-medium).

**Research JSON response**: auto-converted to structured markdown (## Summary / ## Key Findings / ## Sources sections).

---

### 22.9 Markdown Content Rendering — Special Payloads

- **Data analysis** (`tryParseDataAnalysis`): shows `ChartRenderer` (PNG) + optional explanation markdown + "Raw output" `<details>` collapse.
- **Research JSON** (`tryParseResearchJSON`): rendered as structured markdown headings.
- **Multi-source synthesis** (`tryParseMultiSource`): each `[Source N — tool]` block rendered separately with tool badge header.
- **Python code** (`extractPythonCode`): `ExecutionPanel` rendered below markdown.

---

### 22.10 StudioPanel (`StudioPanel.jsx`)

Right column; `glass-light h-full flex flex-col border-l border-border`. Default width 360 px (min 260, max 600).

#### Left resize handle
- `absolute left-0 top-0 bottom-0 w-[1.5px]`; hover: `bg-accent/30 cursor-col-resize`.

#### Panel header (`panel-header`)
- **Grid view**: flask/beaker SVG (`text-text-muted w-4 h-4`) + "Studio" (`text-sm font-semibold`).
- **Drilled-in view**: left-chevron `btn-icon` → "Studio" (text-muted) → right-chevron SVG → active view title (text-text-primary).

#### Action error toast
- `absolute top-4 left-4 right-4 rounded-xl border backdrop-blur-md bg-danger-subtle border-danger-border p-4 z-20 animate-fade-in`.
- Warning triangle in `w-8 h-8 rounded-full bg-danger/20`.
- "Generation Failed" heading (`text-sm font-semibold text-danger-light`) + error detail (xs text-text-secondary) + × dismiss (`btn-icon-sm absolute top-3 right-3`).

#### Grid view (feature card list)
- xs description line (text-muted): "X sources · Generate study materials".
- `space-y-2.5` list of `FeatureCard` components, each offset by 60 ms `animate-fade-up`.
- **Podcast progress bar** (when generating): `rounded-xl p-3 bg-accent/5 border border-accent/10`; accent progress fill + "N%" text-accent font-medium.
- **"Created" section** (after divider): `text-xs font-medium text-text-muted uppercase tracking-wider mb-2` heading; `output-card` items.

**`output-card`** CSS component: `flex items-center gap-3 w-full px-3 py-2.5 rounded-xl hover:bg-surface-overlay border border-transparent hover:border-border transition-all cursor-pointer`.
- Icon box: `output-card-icon bg-accent/10 text-accent-light` (8×8, rounded-lg).
- Title (`text-sm font-medium text-text-primary truncate`) + subtitle (xs text-muted).
- 3-dot hover menu → Rename · Export · Share · Delete (red, border-top separated).

---

### 22.11 Studio — Inline Flashcards View

Activated by clicking a generated flashcard deck in Studio.

#### Top bar
- Card counter: "**N** / total" (`text-xs text-text-secondary tabular-nums`).
- "All" (`btn-secondary text-xs`) → list view.
- "PDF" (`btn-secondary text-xs`) → generates PDF download.

#### Segmented progress bar
- `flex gap-1`; each step: `h-1 flex-1 rounded-full`; past: `bg-border-strong`; current: `bg-accent`; future: `bg-surface-overlay`.

#### Flashcard (3D flip)
- `perspective: 1000px` wrapper. Inner container: `transformStyle: preserve-3d; transition: transform 0.45s cubic-bezier(0.4,0,0.2,1)`.
- **Front (Question)**:  `rounded-xl border border-border bg-surface-raised min-h-[240px]`; header row shows "QUESTION" (10px bold uppercase tracking-[0.14em] text-text-muted) + card number; question text centered (`text-[15px] leading-relaxed font-medium`); footer row: swap-arrows SVG + "Click to reveal answer" (text-muted 11px).
- **Back (Answer)**: identical size, `rotateY(180deg)`; header shows "ANSWER" in `text-accent`; answer text centered.

#### Navigation row
- Three buttons: "Prev" (`btn-secondary flex-1 py-2.5`) + "Flip" (border/surface-raised, center) + "Next" (`btn-primary flex-1 py-2.5`).
- Keyboard hints: `←` `→` Navigate · `Space` Flip (styled `<kbd>` pills).

#### List view (all cards)
- Header: "All Cards" + count + "Back to Study" `btn-primary`.
- Scrollable `space-y-1 max-h-[500px]`: each row is a button `rounded-lg border px-3 py-2.5`; selected: `border-accent bg-accent/5`; others: `border-border hover:bg-surface-overlay`; shows question + truncated answer.

---

### 22.12 Studio — Inline Quiz View

#### Active question screen
- Question counter (`text-xs font-semibold uppercase tracking-wider text-accent`) + score badge (`bg-accent/10 px-2 py-1 rounded-md text-accent text-xs font-bold`).
- Gradient progress bar: `h-1.5 bg-surface-overlay rounded-full`; fill: `bg-gradient-to-r from-accent to-purple-500`.
- Question text: `text-lg font-semibold text-text-primary leading-snug px-1`.
- **Answer options** (`space-y-3`): each `w-full p-4 text-left rounded-xl border-2 transition-all duration-300 text-sm flex items-center justify-between group`.
  - Default: `border-border bg-surface-raised hover:-translate-y-0.5 hover:shadow-md hover:border-accent/50 hover:bg-accent/5`.
  - Correct: `border-success bg-success-subtle shadow-[0_0_15px_rgba(16,185,129,0.15)]` + green circle checkmark (✓).
  - Wrong selection: `border-danger bg-danger-subtle` + red circle ✗.
  - Other options after answer: `border-border bg-surface opacity-40 grayscale-[50%]`.

#### Feedback panel (after selection)
- Correct: `bg-gradient-to-r from-success-subtle to-success-subtle/50 border-success-border p-5 rounded-xl animate-fade-up`; "Excellent! That's correct." with bouncing checkmark icon.
- Wrong: same layout in danger colors; shows correct answer in `bg-surface/50 p-3 rounded-lg border`.
- Optional explanation below `border-t border-border/40`.
- "Next Question →" / "See Final Results ✨" `btn-primary w-full py-3.5`.

#### Results screen
- `glass rounded-2xl animate-fade-up min-h-[300px] border border-accent/20 text-center py-10`.
- 24×24 rounded-full `bg-gradient-to-tr from-accent to-purple-500 shadow-glow animate-scale-in` with emoji: 🏆 (≥80%) / ⭐ (≥50%) / 📚 (<50%).
- Score: gradient text `from-accent to-purple-400 text-2xl font-bold`.
- "Retake Quiz" `btn-primary px-8 py-3 rounded-xl hover:-translate-y-1`.

---

### 22.13 AgentThinkingBar (`chat/AgentThinkingBar.jsx`)

Shown above the input while agent runs.

- `flex items-center gap-3 px-4 py-3 mb-2 rounded-2xl border animate-fade-in`.
- Normal: `bg-accent/5 border-accent/20`. Repair mode: `bg-amber-500/5 border-amber-500/25`.
- **Spinner**: 5×5 div with `border-2 border-accent/20` base circle + `border-t-accent animate-spin` overlay. Repair mode: 🔧 emoji `animate-pulse`.
- **Step icon** (emoji derived from tool name) + **step label** (`text-sm text-text-secondary truncate flex-1`). Repair: label is `text-amber-400`.
- Right badges: "Step N" pill (`text-xs px-2 py-0.5 rounded-full bg-surface-overlay text-text-muted tabular-nums`) + elapsed time (xs text-muted tabular-nums).

---

### 22.14 SlashCommandDropdown (`chat/SlashCommandDropdown.jsx`)

Floating menu above input, triggered by `/` keystroke.

- `absolute bottom-full left-0 right-0 mb-2 z-50 animate-fade-in`.
- Container: `bg-surface-raised border border-border rounded-xl shadow-elevated overflow-hidden max-h-[320px] overflow-y-auto`.
- Header (`px-3 py-2 border-b border-border/50`): "Slash Commands" (`text-xs font-medium text-text-muted`).
- Each command row (`flex items-center gap-3 px-3 py-2.5`); active: `bg-accent/10`; hover: `bg-surface-overlay/50`:
  - Command chip: `w-16 text-xs font-mono font-semibold rounded-md px-1.5 py-0.5 border`; border/bg/text colors derived from `cmd.color` with `40`/`15` opacity.
  - Label (`text-sm text-text-primary`) + description (`text-xs text-text-muted truncate`).

---

### 22.15 AgentActionBlock (`chat/AgentActionBlock.jsx`)

Collapsible step log drawer shown below AI messages that were generated by the agent.

- Outer: `rounded-xl border overflow-hidden mb-3`.
  - Running step: `border-accent/40 bg-accent/5`.
  - Complete step: `border-border/30 bg-surface-overlay/40`.
- **Step row button** (`flex items-center gap-3 px-3 py-2.5`):
  - Step number (xs tabular-nums text-muted) or spinning `border-t-accent` disc for running step.
  - **Tool badge**: `rounded-full border font-medium text-xs px-2 py-0.5`; color per tool (blue=RAG, purple=research, green=Python, yellow=quiz, pink=flashcard, orange=slides, cyan=data, indigo=file, teal=execute).
  - Step label (`text-sm text-text-secondary truncate flex-1`).
  - Time taken (xs tabular-nums text-muted), status mark (✓ green / ✗ red), chevron ▶.
- **Expanded details** (code + output):
  - Code: `SyntaxHighlighter` in one-dark theme, `bg-surface-sunken`, max-h-56.
  - Output: `<pre>` monospace in `bg-surface border border-border/30 max-h-40`; running: green pulse dot indicator.

---

### 22.16 GeneratedFileCard (`chat/GeneratedFileCard.jsx`)

Download chip shown at bottom of AI messages that produced files.

- `inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-surface-overlay border border-border text-sm hover:bg-surface-raised hover:border-accent/30 transition-all`.
- File-type-specific colored icon (small SVG, 4×4).
- Filename (`text-text-primary text-xs font-medium truncate max-w-[140px]`) + size (xs text-muted).
- Download arrow icon on right.

---

### 22.17 UploadDialog (`UploadDialog.jsx`)

Full-screen modal, `max-w-[680px] max-h-[88vh] rounded-2xl` with `backdrop-filter: blur(6px)`.

#### Header
- `px-6 py-5 border-b`.
- 9×9 rounded-xl `bg-accent-subtle` box + upload-cloud SVG (`text-accent-light`) + "Add Sources" title (base font-semibold) + subtitle (xs text-muted) + X `btn-icon w-8 h-8`.

#### Tab bar
- `flex gap-1 p-1 rounded-xl bg-surface-overlay`.
- 3 tabs: "Upload Files" / "Website / URL" / "Paste Text"; each: `flex-1 px-3 py-2 rounded-lg text-sm font-medium`; active: `bg-surface-raised shadow-[0_1px_4px_rgba(0,0,0,0.15)] text-text-primary`; inactive: `text-text-muted hover:text-text-secondary`.

#### Files tab
- Drop zone: `rounded-2xl border-2 border-dashed`; default `border-border hover:border-accent/30 hover:bg-surface-overlay`; drag-active: `border-accent bg-accent/5`.
  - Icon box 14×14 `rounded-2xl`; drag-active: `scale-110 bg-accent-subtle border-accent-border`.
  - "Drag & drop files here" / "Drop files here" (sm font-medium text-text-primary).
  - "or click to browse • max N MB per file" (xs text-muted).
  - `btn-primary text-sm px-5 py-2` "Choose Files" button (spinning if loading).
- **Format chips grid** (2 columns): each chip `rounded-xl px-3 py-2.5 bg-surface-overlay border-border-light`; emoji icon + label (xs font-medium text-text-secondary) + format list (2xs text-muted truncate).

#### Web/URL tab
- URL input with `LinkIcon` on left + `btn-primary` "Add Source" button.
- 2×2 info cards grid (`bg-surface-overlay border-border-light rounded-xl px-3.5 py-3`): 🌐 Any Website / ▶️ YouTube / 📰 News & Wikis / 🔍 Auto Detect.

#### Text tab
- Title input (`input`) + 7-row textarea (`input resize-none`) + `btn-primary w-full` "Add Text Source".

#### Toast (inside modal)
- `absolute bottom-4 left-1/2 -translate-x-1/2 ... animate-fade-up rounded-xl`; error: `bg-danger-subtle border-danger-border text-danger-light`; success: green equivalent.

#### Loading overlay
- `absolute inset-0 rounded-2xl bg-backdrop backdrop-blur-[2px] flex flex-col items-center justify-center`; `loading-spinner w-8 h-8` + "Processing your source…".

---

### 22.18 Modal (`Modal.jsx`)

Reusable dialog wrapper used throughout (flashcard/quiz config, rename dialogs, etc.).

- Backdrop: `.modal-backdrop` = `fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center animate-fade-in`.
- Box: `.modal` = `bg-surface-raised border border-border rounded-2xl shadow-glass w-full animate-scale-in`.
- Header (`.modal-header`): `flex items-center justify-between px-6 py-4 border-b border-border`; optional `text-accent` icon + title (`text-lg font-semibold text-text-primary`) + `btn-icon-sm` X button.
- Body (`.modal-body`): `px-6 py-4`.
- Footer (`.modal-footer`): `flex items-center justify-end gap-2 px-6 py-4 border-t border-border`.

---

### 22.19 Flashcard Config Dialog

Opens before flashcard generation.

- Uses `Modal` (`max-w-xl`): flashcard stack icon in header.
- "Customize your flashcard generation settings." (sm text-muted).
- **Number of Flashcards** (`form-group`): `input` type number 1–50; placeholder "AI decides".
- **Difficulty** chip group: "Easy" / "Medium" / "Hard" — `.chip` pills; selected: `.chip.selected` (accent background + accent text + accent border).
- **Additional Instructions**: 3-row `.textarea`.
- "Generate Cards" `btn-primary w-full` (⚡ icon + spinning if loading) + "Cancel" `btn-secondary w-full`.

---

### 22.20 Quiz Config Dialog

Identical structure to Flashcard Config Dialog, but with:
- Clipboard-check icon in header.
- "Number of Questions" field.
- Same difficulty chips.
- "Generate Quiz" button.

---

### 22.21 Studio — Inline Explainer View

Shows after an explainer video is generated.

- `<video controls className="w-full" style={{ maxHeight: '300px' }}>` black background `rounded-lg overflow-hidden`.
- Duration + chapter count row (xs text-muted, space-between).
- **Chapters list** (`space-y-1 max-h-48 overflow-y-auto`): each row `flex items-center gap-3 text-xs text-text-muted py-1.5 px-2 rounded hover:bg-surface-raised`; timestamp in monospace (`font-mono text-text-secondary`) + chapter title (`text-text-primary truncate`).
- "Download Video" `btn-primary w-full` with download arrow icon.

---

### 22.22 Podcast Studio (Studio → Podcast view)

Loaded via `PodcastStudio` component when `activeView === 'podcast'` in StudioPanel.

- Existing podcast sessions listed as `output-card` items at bottom of the grid: icon box (`bg-accent/10 PodcastIcon`), title, duration + language pill.
- Hover: trash icon (`text-red-400 hover:bg-red-500/10`) appears on right.
- The podcast progress bar (lines 870–890 in StudioPanel) is a `rounded-xl p-3 bg-accent/5 border border-accent/10` container with an accent-colored progress fill and "N%" label.

---

### 22.23 FeatureCard (`FeatureCard.jsx`)

Used in Studio grid to represent each generatable feature.

- `.feature-card group cursor-pointer flex items-center gap-3 px-3 py-3.5 rounded-xl hover:bg-surface-overlay border border-transparent hover:border-border transition-all`.
- **Icon box** (`.feature-card-icon`): 9×9 `rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0`; feature-specific colored icon SVG.
- **Text area** (`flex-1 min-w-0`):
  - Title: `text-sm font-medium text-text-primary group-hover:text-accent transition-colors`.
  - Description / status: `text-xs text-text-muted truncate group-hover:text-text-secondary`. While loading: "Generating…".
- **Right indicator** (`flex-shrink-0`):
  - Default: chevron-right SVG (`w-4 h-4 text-text-muted group-hover:translate-x-0.5 group-hover:text-text-secondary`).
  - Loading: red `bg-red-500/15 text-red-400 p-1.5 rounded-lg` stop-square button.

---

### 22.24 CommandBadge (`chat/CommandBadge.jsx`)

Shown inside the chat input when a slash command is active.

- `inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold`.
- Color matches the command's `cmd.color` (border/bg/text with opacity variants).
- Shows command name + × dismiss button.

---

### 22.25 Key CSS Animation Classes

| Class | Effect |
|---|---|
| `.animate-fade-in` | `opacity: 0→1` over 200 ms |
| `.animate-scale-in` | `scale(0.95)→scale(1)` + fade |
| `.animate-fade-up` | `translateY(8px)→0` + fade |
| `.streaming-pulse` | Pulsing glow on AI avatar during streaming |
| `.streaming-cursor` | Blinking vertical bar after streaming text |
| `.typing-indicator span` | Three-dot bounce-stagger animation |
| `.loading-spinner` | Rotating border (border-t-accent) |
| `spin` (keyframe) | Used inline for custom spinners (`0.8s linear infinite`) |

---

### 22.26 Form & Input Components (CSS Classes)

All form elements are styled via `@layer components` in `index.css`.

| Class | Description |
|---|---|
| `.input` | `w-full rounded-lg bg-surface-raised border border-border px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:ring-2 ring-accent/20` |
| `.textarea` | Same as `.input` with `resize-none` |
| `.form-group` | `flex flex-col gap-1.5` wrapper |
| `.form-label` | `text-sm font-medium text-text-secondary` |
| `.form-label-hint` | `text-xs text-text-muted font-normal` |
| `.chip` | `px-3 py-1.5 rounded-lg border border-border text-sm text-text-secondary hover:border-accent/50 hover:bg-accent/5 transition-all` |
| `.chip.selected` | `border-accent bg-accent/10 text-accent` |
| `.chip-group` | `flex flex-wrap gap-2` |
| `.btn-primary` | `inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all` |
| `.btn-secondary` | Same shape, `bg-surface-raised border border-border text-text-secondary hover:bg-surface-overlay hover:text-text-primary` |
| `.btn-ghost` | Transparent, `hover:bg-surface-overlay text-text-secondary` |
| `.btn-icon` | 8×8, `rounded-lg hover:bg-surface-overlay` |
| `.btn-icon-sm` | 6×6 equivalent |

