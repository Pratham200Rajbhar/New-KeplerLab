<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# KeplerLab — Complete UI Master Plan

### Every screen · Every dialog · Every component · Every state · Every micro-detail


***

## GLOBAL DESIGN SYSTEM

### Color Palette

**Backgrounds (darkest → lightest):**

- Canvas base: `#07080c` — the deepest background, app shell
- Surface primary: `#0a0b0f` — main panel backgrounds
- Surface raised: `#0f1117` — cards, modals, elevated containers
- Surface overlay: `#161820` — dropdowns, tooltips, popovers
- Surface hover: `#1c1e28` — hover state fills
- Surface sunken: `#050608` — code blocks, inset areas

**Brand / Accent:**

- Kepler Blue primary: `#4f6ef7`
- Kepler Blue hover: `#6b87f8`
- Kepler Blue pressed: `#3d5ce6`
- Kepler Blue subtle bg: `rgba(79,110,247,0.08)`
- Kepler Blue border: `rgba(79,110,247,0.35)`
- Kepler Blue glow: `rgba(79,110,247,0.20)`

**Secondary accents (feature-specific):**

- Podcast / Audio: `#10b981` (emerald)
- Quiz / Exam: `#f59e0b` (amber)
- Mind Map: `#8b5cf6` (violet)
- Explainer Video: `#ef4444` (red)
- Presentation: `#06b6d4` (cyan)
- Research / Agent: `#f97316` (orange)

**Text:**

- Primary: `rgba(255,255,255,0.92)`
- Secondary: `rgba(255,255,255,0.65)`
- Muted: `rgba(255,255,255,0.38)`
- Disabled: `rgba(255,255,255,0.22)`
- Inverse (on light bg): `#07080c`

**Borders:**

- Subtle: `rgba(255,255,255,0.06)`
- Default: `rgba(255,255,255,0.10)`
- Strong: `rgba(255,255,255,0.18)`
- Focus: `#4f6ef7`

**Semantic:**

- Success: `#16a34a` · bg: `rgba(22,163,74,0.10)`
- Warning: `#d97706` · bg: `rgba(217,119,6,0.10)`
- Error: `#dc2626` · bg: `rgba(220,38,38,0.10)`
- Info: `#0ea5e9` · bg: `rgba(14,165,233,0.10)`

***

### Typography

**Font families:**

- UI / Prose: `Inter` (Google Fonts) → `system-ui` fallback
- Code / Mono: `JetBrains Mono` → `Fira Code` → `monospace` fallback
- Display headings (auth, marketing): `Inter` 700–800 weight

**Size scale:**

- `2xs`: 10px / line-height 14px — labels, timestamps, badges
- `xs`: 11px / 16px — metadata, captions, helper text
- `sm`: 12px / 18px — secondary body, subtitles
- `base`: 13px / 20px — primary body text (global base)
- `md`: 14px / 22px — slightly emphasized body
- `lg`: 16px / 24px — section headings, card titles
- `xl`: 20px / 28px — page headings
- `2xl`: 24px / 32px — modal titles, feature headings
- `3xl`: 32px / 40px — auth page headings
- `4xl`: 48px / 56px — marketing/branding text

**Weight usage:**

- `400` — body text, descriptions
- `500` — labels, secondary headings
- `600` — primary headings, button labels, names
- `700` — display text, auth hero, emphasis

***

### Spacing System

Base unit: `4px`
Scale: `2, 4, 6, 8, 10, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96`

**Named spacings:**

- Compact inner padding: `8px 12px`
- Standard inner padding: `12px 16px`
- Comfortable inner padding: `16px 20px`
- Section gap: `24px`
- Panel gap: `32px`

***

### Border Radius

- `xs`: 4px — inline badges, tiny chips
- `sm`: 6px — small buttons, tags
- `md`: 8px — input fields, small cards
- `lg`: 10px — standard cards
- `xl`: 12px — panel sections
- `2xl`: 16px — modals, large cards
- `3xl`: 20px — bottom sheets
- `4xl`: 24px — floating composure bar
- `full`: 9999px — pills, avatars, toggle buttons

***

### Shadow System

- `shadow-xs`: `0 1px 2px rgba(0,0,0,0.3)` — subtle lift
- `shadow-sm`: `0 2px 8px rgba(0,0,0,0.35)` — card default
- `shadow-md`: `0 4px 16px rgba(0,0,0,0.4)` — elevated card
- `shadow-lg`: `0 8px 32px rgba(0,0,0,0.5)` — modals
- `shadow-xl`: `0 16px 60px rgba(0,0,0,0.6)` — fullscreen overlays
- `shadow-glow-blue`: `0 0 0 1px rgba(79,110,247,0.4), 0 0 20px rgba(79,110,247,0.15)`
- `shadow-glow-green`: `0 0 0 1px rgba(16,185,129,0.4), 0 0 20px rgba(16,185,129,0.12)`
- `shadow-inner-sunken`: `inset 0 1px 4px rgba(0,0,0,0.4)` — input fields

***

### Animation System

**Duration tokens:**

- `instant`: 80ms — hover background fills
- `fast`: 120ms — icon states, dot indicators
- `quick`: 180ms — button states, badge transitions
- `standard`: 250ms — panel transitions, card hovers
- `gentle`: 350ms — modal entrance, drawer slides
- `slow`: 500ms — page-level transitions
- `very-slow`: 800ms — waveform animations, skeleton shimmer

**Easing tokens:**

- `ease-snap`: `cubic-bezier(0.16, 1, 0.3, 1)` — spring-like, used for entrances
- `ease-smooth`: `cubic-bezier(0.4, 0, 0.2, 1)` — standard material easing
- `ease-out-expo`: `cubic-bezier(0.19, 1, 0.22, 1)` — fast-out, used for exits
- `ease-bounce`: `cubic-bezier(0.34, 1.56, 0.64, 1)` — playful micro-bounce (used sparingly: toggles, checkmarks)

**Named animation keyframes:**

- `fade-in`: opacity 0→1
- `fade-up`: opacity 0→1 + translateY 8px→0
- `fade-down`: opacity 0→1 + translateY -8px→0
- `scale-in`: scale 0.94→1 + opacity 0→1
- `scale-out`: scale 1→0.96 + opacity 1→0
- `slide-in-right`: translateX 24px→0 + opacity 0→1
- `slide-in-left`: translateX -24px→0 + opacity 0→1
- `slide-up`: translateY 16px→0 + opacity 0→1
- `shimmer`: background-position -200%→200% (skeleton loading)
- `spin`: rotate 0→360deg (spinner)
- `spin-slow`: rotate 0→360deg over 3s (logo ambient)
- `pulse-soft`: opacity 1→0.6→1 (status indicators)
- `waveform-bar`: scaleY 0.3→1→0.3 (audio visualizer bars)
- `card-flip`: rotateY 0→180deg (flashcard)
- `orbit`: rotate around center point (mind map placeholder)
- `progress-slide`: translateX -100%→100% (indeterminate progress bar)

***

### Interactive State Definitions (applied globally)

Every interactive element must have all of these:

- **Default** — base appearance
- **Hover** — background shift + border brightening within `instant` (80ms)
- **Active/Pressed** — `scale(0.97)` + slight background darken within `instant` (80ms)
- **Focus-visible** — `outline: 2px solid #4f6ef7; outline-offset: 2px` (keyboard only, not mouse)
- **Disabled** — `opacity: 0.35`, `cursor: not-allowed`, no hover/active effects
- **Loading** — spinner replaces label, width locked to prevent layout shift

***

### Button System

**Primary (`btn-primary`):**

- Background: `linear-gradient(135deg, #4f6ef7, #7c3aed)`
- Text: white, `sm font-semibold`
- Padding: `8px 16px`, `border-radius: full`
- Border: none
- Hover: gradient shifts to lighter variant + `shadow-glow-blue`
- Active: `scale(0.97)` + gradient darkens
- Loading: gradient stays, spinner appears left of text

**Secondary (`btn-secondary`):**

- Background: transparent
- Border: `1px solid rgba(255,255,255,0.18)`
- Text: `text-primary sm font-medium`
- Hover: `bg-white/6`
- Active: `bg-white/10 scale(0.97)`

**Ghost (`btn-ghost`):**

- Background: transparent, no border
- Text: `text-secondary sm`
- Hover: `bg-white/5 text-primary`
- Active: `bg-white/8 scale(0.97)`

**Danger (`btn-danger`):**

- Background: `rgba(220,38,38,0.12)`
- Border: `1px solid rgba(220,38,38,0.25)`
- Text: `#ef4444`
- Hover: `bg-red/20 border-red/50`

**Icon (`btn-icon`):**

- Dimensions: `32×32px` or `28×28px` (small variant)
- Background: transparent, no border
- Border-radius: `md` (8px)
- Hover: `bg-white/8`
- Active: `bg-white/12 scale(0.93)`

**Full-width CTA:**

- Same as primary but `width: 100%`, height `44px`, text `base font-semibold`
- Used in modals, config dialogs, bottom of forms

***

### Input Field System

**Text input:**

- Height: `36px`
- Background: `rgba(255,255,255,0.05)`
- Border: `1px solid rgba(255,255,255,0.10)`
- Border-radius: `md` (8px)
- Padding: `8px 12px`
- Font: `base`, color `text-primary`
- Placeholder: `text-muted`
- Box-shadow: `shadow-inner-sunken`
- Focus: border → `#4f6ef7`, box-shadow → `shadow-glow-blue` + remove inner-sunken
- Error state: border → `#dc2626`, box-shadow → `0 0 0 1px rgba(220,38,38,0.4)`
- Disabled: `opacity: 0.4`

**Textarea:**

- Same as text input, `min-height: 80px`, resize vertical only
- Scrollbar styled: `4px wide, bg-white/10, rounded`

**Search input:**

- Same as text input with a search icon inside left (`16px`, `text-muted`)
- Input left-padding: `36px` to accommodate icon

**Floating label pattern (auth only):**

- Label starts at vertical center of input in `base text-muted`
- On focus or when value is present: label animates up to `xs` size, shifts to top-left corner, color → `text-accent`

**Select / Dropdown:**

- Looks identical to text input
- Custom dropdown panel: `bg-surface-overlay border border-white/10 rounded-xl shadow-lg`
- Options: `px-3 py-2 text-sm text-secondary hover:bg-white/6 hover:text-primary`
- Active option: `bg-accent-subtle text-accent`
- Searchable: a search input at top of dropdown panel

***

### Badge / Chip System

**Status badge:**

- Pill shape, `xs font-medium`, `px-2 py-0.5`
- Success: green bg + text
- Warning: amber bg + text
- Error: red bg + text
- Processing: blue bg + text + animated pulse dot before text
- Pending: gray bg + text

**Feature type chip:**

- Slightly larger: `sm`, `px-3 py-1`
- Each feature has its own color (listed in secondary accents above)
- Can have a leading icon (16px)

**Source type chip:**

- `xs`, `px-2 py-0.5`, rounded-full
- PDF → red/20 bg
- YouTube → orange/20 bg
- Web → blue/20 bg
- Audio → green/20 bg
- Image → violet/20 bg
- Text → gray/20 bg

**Removable chip:**

- Chip with `[×]` button on right (12px, `text-muted`, hover → `text-primary`)
- Used in config dialogs for selected sources

***

### Toast / Notification System

**Position:** Bottom-right corner, `20px` from edges
**Stack:** Max 3 visible; older toasts compress (height reduces to 8px stacked behind newer)
**Width:** `320px` fixed
**Structure per toast:**

- Container: `bg-surface-raised border border-white/10 rounded-xl shadow-xl`
- Left accent border: `4px solid` in semantic color
- Inside: icon (16px) + title (`sm font-semibold`) on first line + optional body (`xs text-secondary`) on second line + optional action button (ghost, right-aligned)
- Top-right: `[×]` close button (appears on hover)
- Bottom: thin progress bar showing time-to-dismiss (depletes left-to-right)

**Auto-dismiss:** 4 seconds. Hovering pauses the timer.
**Entrance:** `slide-in-right` + `fade-up` combined, 200ms
**Exit:** `scale-out` + `fade-out`, 150ms

**Types:**

- Success: green left-border + checkmark icon
- Error: red left-border + `!` icon + shake animation on entrance
- Warning: amber left-border + warning triangle icon
- Info: blue left-border + `i` icon

***

### Skeleton Loading System

**Base skeleton element:**

- Background: `rgba(255,255,255,0.06)`
- Shimmer overlay: `linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.04) 50%, transparent 100%)` — animates `background-position` over 1.5s loop
- Border-radius: matches the element being replaced

**Content-aware skeletons:**

- Notebook card skeleton: exact card dimensions — gradient bar at top (static placeholder color) + 2 text lines (80% width, 60% width) + bottom row
- Source item skeleton: icon square (28×28) + 2 text lines + status dot area
- Chat message skeleton: 3–4 lines at varying widths (90%, 75%, 85%, 50%)
- Feature card skeleton: icon area + 2 text lines
- Podcast segment skeleton: avatar circle + 2 text lines

***

### Scrollbar Styling (global)

- Width: `4px` (vertical), `4px` (horizontal)
- Track: transparent
- Thumb: `rgba(255,255,255,0.12)`, `border-radius: full`
- Hover on thumb: `rgba(255,255,255,0.20)`
- Only visible on hover of the scrollable container

***

### Focus / Keyboard Navigation

- All interactive elements tabbable in logical order
- `focus-visible` ring: `2px solid #4f6ef7, offset 2px`
- Skip-to-content link: visible only on focus, positioned top-left
- `Escape` key: closes any open dialog, drawer, dropdown, tooltip
- `Enter` / `Space` on non-input focused elements: triggers click action

***

## SCREEN 1: AUTH PAGE (`/auth`)

### Page Layout

- Full-bleed: `100vw × 100vh`, no scroll
- Two-column split: `60% left branding panel` + `40% right form panel`
- On screens under `768px`: left panel hidden, form takes full width


### Left Branding Panel

- Background: `#07080c` with a subtle radial gradient vignette (`rgba(79,110,247,0.08)` at center fading to transparent)
- Particle field: 40 small dots (`3–5px`, `rgba(79,110,247,0.3–0.6)`) scattered randomly, each drifting in a slow random direction, looping infinitely — pure CSS `@keyframes` with `nth-child` offsets
- Subtle grid overlay: `background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)`, `background-size: 40px 40px`
- KeplerLab logomark (orbit SVG) — `64px`, centered horizontally, positioned at `30% from top`
- Tagline: `"Your AI-Powered\nStudy Universe"` — `4xl`, `font-weight: 800`, `line-height: 1.15`, gradient text fill: `linear-gradient(135deg, #ffffff, #a5b4fc, #4f6ef7)`
- Subtitle below tagline: `"Upload anything. Understand everything."` — `md`, `text-secondary`
- Feature proof row at `70% from top`: 3 items horizontally with `gap-8`
    - Each item: a `32×32` icon with `bg-accent-subtle rounded-lg` + label text `sm text-secondary`
    - Item 1: brain icon + `"RAG Chat"`
    - Item 2: waveform icon + `"AI Podcasts"`
    - Item 3: mind-map icon + `"Mind Maps"`


### Right Form Panel

- Background: `bg-[#0a0b0f]`
- Vertical centering: flexbox `align-items: center justify-content: center`
- Form card: `480px max-width`, `width: 90%`, `bg-white/3 backdrop-blur-2xl border border-white/8 rounded-3xl px-8 py-10 shadow-xl`

**Form card internals (top to bottom):**

1. **Logo + brand:** `32px` orbit logo SVG + `"KeplerLab"` wordmark `xl font-semibold text-primary` — horizontal, centered
2. **Spacing:** `32px`
3. **Tab switcher:** Two tabs — `"Sign in"` and `"Create account"` — inside a pill container `bg-white/5 rounded-full p-1`. Each tab: `px-6 py-2 rounded-full text-sm font-medium`. Active tab: `bg-white/12 text-primary shadow-sm`. Inactive: `text-muted`. Transition between tabs: sliding background pill animates `left` position over `200ms ease-snap`
4. **Spacing:** `28px`
5. **Form fields** (described per tab below)
6. **Spacing:** `20px`
7. **Submit button:** full-width CTA, `44px` height, gradient primary, text changes per tab
8. **Spacing:** `16px`
9. **Divider row** (sign-in only): `"—— or ——"` with muted text, centered
10. **OAuth placeholder row** (sign-in only): `"More sign-in options coming soon"` — `xs text-muted`, centered, italic

**Login tab fields:**

- Email input with floating label `"Email address"`, `type=email`, full-width
- Password input with floating label `"Password"`, `type=password`, full-width, show/hide toggle button inside right side (eye icon — toggles `type` between `password`/`text`)
- Forgot password link: `xs text-accent hover:underline` right-aligned below password field (placeholder, no functionality yet)
- Submit button text: `"Sign in →"`

**Signup tab fields:**

- Username input with floating label `"Username"`, full-width
- Email input with floating label `"Email address"`, full-width
- Password input with floating label `"Create password"`, full-width, show/hide toggle
- Password strength indicator: a `4px` bar below the password field that fills and changes color: red (weak) → amber (medium) → green (strong) based on character diversity
- Submit button text: `"Create account →"`

**Error state:**

- When error occurs: the form card's border transitions from `border-white/8` → `border-red/40` with a single pulse animation (glows red once then settles to the new border color)
- Error message: `xs text-red-400` appears below the submit button with a `!` icon prefix
- The specific erroring field gets a red border

**Loading state (during submit):**

- Submit button: text disappears, spinner appears in center, button remains same size
- Form fields: `opacity: 0.6`, `pointer-events: none`

**Success transition (after login):**

- Form card: `scale(0.96) opacity(0)` over `300ms` then navigate

***

## SCREEN 2: HOME / DASHBOARD (`/`)

### Page Layout

- Full height: `100vh`, `overflow: hidden`
- Left rail: `72px wide`, fixed, full height
- Content area: `calc(100vw - 72px)`, scrollable


### Left Rail

- Background: `bg-[#0a0b0f] border-r border-white/6`
- Top: KeplerLab orbit logo `32px`, centered, `24px` from top — ambient slow rotation animation (`spin-slow` — 8s loop)
- Nav items (icon-only): vertical stack, `gap-2`, centered, `40px from logo bottom`
    - Each nav item: `48×48px btn-icon`, icon `20px`
    - Items: Home (house) · All Notebooks (grid) · Search (magnifier) · Settings (gear, bottom-pinned)
    - Active item: `bg-accent-subtle text-accent`
    - Hover: tooltip label appears to the right — `bg-surface-overlay border border-white/10 rounded-lg px-3 py-1.5 text-sm shadow-md`, entrance `slide-in-right 150ms`
- Bottom: user avatar circle `36×36px`, `8px from bottom`
    - Avatar: solid circle `bg-gradient-to-br from-[#4f6ef7] to-[#7c3aed]`, initials `xs font-semibold text-white`, auto-generated from `username[0] + username[1]` or `username[0]` if single char
    - Click: opens user account popover


### User Account Popover (from avatar click)

- Position: `bottom: 56px, left: 80px` (above and to right of avatar)
- Dimensions: `240px wide`
- Container: `bg-surface-overlay border border-white/10 rounded-2xl shadow-xl p-2`
- Content (top to bottom):
    - User info row: avatar `40×40` + username `sm font-semibold` + email `xs text-muted`
    - `border-t border-white/6 my-2`
    - Menu item: `Account Settings` — ghost, full-width, left-aligned text, settings icon left (placeholder, no route yet)
    - Menu item: `Keyboard Shortcuts` — ghost, `Cmd+/` badge right-aligned (placeholder)
    - Menu item: `Theme` — ghost, sun/moon icon, current theme label right-aligned
    - `border-t border-white/6 my-2`
    - Menu item: `Sign out` — ghost, `text-red-400 hover:bg-red/8`, logout icon left
- Entrance: `scale-in` from bottom-left origin, `150ms ease-snap`
- Dismisses on outside click or `Escape`


### Content Area Header (inside content zone)

- `px-8 pt-8 pb-0`
- Greeting text: `"Good morning, [username]"` — `2xl font-semibold text-primary`
- Sub-greeting: current date formatted as `"Monday, 2 March 2026"` — `sm text-muted`
- Right side: `[+ New Notebook]` primary button


### Notebooks Grid

- Container: `px-8 pt-6`
- Top bar: `"Your Notebooks"` label `base font-semibold text-secondary` + sort dropdown right-aligned (`"Last modified ↓"` default options: Last modified · Name A–Z · Date created · Most sources)
- Grid: `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`, `gap-4`

**Notebook Card:**

- Dimensions: `min-height: 160px`
- Container: `bg-surface-raised border border-white/8 rounded-2xl overflow-hidden cursor-pointer`
- Hover: `border-white/18 shadow-md translateY(-2px)`, transition `standard`
- **Accent gradient bar** at top: `height: 4px`, gradient determined by notebook ID hash (5 preset gradients cycling: blue-purple · teal-green · orange-red · pink-rose · yellow-amber)
- Card body padding: `16px`
- Notebook name: `base font-semibold text-primary`, `1 line max, text-overflow: ellipsis`
- Description: `sm text-secondary`, `2 lines max, -webkit-line-clamp: 2`
- Bottom row (always at card bottom, `margin-top: auto`):
    - Source count pill: `xs text-muted bg-white/5 rounded-full px-2 py-0.5` — `"N sources"`
    - Last-activity time: `xs text-muted` right-aligned — relative format: `"2 hours ago"`, `"Yesterday"`, `"3 days ago"`
- Hover reveals kebab `[⋯]` button at `top-right: 12px 12px` — `btn-icon 28×28px`, entrance `fade-in 120ms`

**Notebook Card Kebab Menu:**

- `bg-surface-overlay border border-white/10 rounded-xl shadow-lg p-1`, `width: 160px`
- Items: `Rename` · `Duplicate` (placeholder) · `Delete`
- Delete item: `text-red-400 hover:bg-red/8`
- Appears below kebab button, slight right-offset, entrance `scale-in 150ms`

**New Notebook Creation Card:**

- Same grid position as notebook cards — a dashed-border card
- Default state: `border: 2px dashed rgba(255,255,255,0.12)`, `bg-transparent`, centered `+ New Notebook` text with a large `+` icon
- Hover: border brightens to `rgba(79,110,247,0.4)`, background tints to `rgba(79,110,247,0.04)`, content shifts to show expanded creation form
- **Expanded on click (not a modal — expands inline within the card):**
    - Card height animates to `280px`
    - Inside: name input (auto-focused) + description textarea (2 rows) + template chip row + `[Create →]` button
    - Template chips: `Blank · Lecture Notes · Research · Exam Prep · Book Summary` — horizontal scroll, `xs`, pill-shaped
    - Selecting a template pre-fills the description textarea
    - `[Create →]` disabled until name is non-empty

**Empty Dashboard State:**

- No grid, just a centered block in the content area
- Animated orbit ring: 3 dots orbiting a center point (pure CSS)
- Heading: `"Your study universe is empty"` — `xl font-semibold`
- Body: `"Create your first notebook to start learning with AI"` — `sm text-secondary`
- `[Create Notebook]` primary button below

**Loading State (fetching notebooks on mount):**

- 6 notebook card skeletons in the grid
- Each skeleton: gradient bar placeholder at top (static gray) + 2 shimmer lines + bottom row shimmer

***

## SCREEN 3: WORKSPACE (`/notebook/:id`)

### Page Layout

4 zones, horizontal:

```
[Left Rail 72px] | [Sidebar 280px] | [Chat Panel flex-1] | [Studio Drawer 380px]
```

- All zones: `height: 100vh`, `overflow: hidden` at page level, internal scroll within zones
- No top header bar — header is embedded at the top of the Chat Panel zone
- Panels separated by `1px` dividers (`rgba(255,255,255,0.06)`)

**Panel Collapse Behavior:**

- Sidebar: collapsible via a `[◀]` / `[▶]` toggle button on its right edge
    - Collapsed width: `0px` (fully hidden), transition `350ms ease-smooth`
    - Toggle button: `20×20px` circle, `bg-surface-overlay border border-white/10`, positioned absolutely on the right edge
- Studio Drawer: collapsible via a `[▶]` / `[◀]` toggle on its left edge, same pattern
- Collapse state persisted in `localStorage` keyed by `notebook-{id}-layout`

***

## SCREEN 4: WORKSPACE HEADER (embedded in Chat Panel top)

- Height: `48px`
- Background: `bg-[#0a0b0f]/80 backdrop-blur-xl border-b border-white/6`
- Layout: 3 zones — left, center, right

**Left zone:**

- `[←]` back-to-home chevron button `btn-icon` — tooltip `"Back to notebooks"` on hover
- Divider: `1px` vertical, `rgba(255,255,255,0.08)`, `height: 20px`
- Notebook name: clicking switches it inline to a text `<input>` — input inherits the same text styling, no visible border change until focused, auto-selects all text on click, saves on `Enter` or blur, cancels on `Escape`
- While in edit mode: a save indicator `"Press Enter to save"` appears below in `xs text-muted`

**Center zone:**

- Model indicator pill: `bg-white/6 border border-white/10 rounded-full px-3 py-1 text-xs text-secondary`
- Shows active LLM provider: a `8px` colored dot + provider name: `● Gemini Flash` or `● Llama 3` etc.
- Dot color: green if model loaded, amber if degraded, red if offline
- Clicking: opens a small popover with model details (current provider, model name, status) — read-only for now

**Right zone:**

- Sources selected count: when `> 0` sources are selected, shows `"N sources selected"` as a blue pill `bg-accent-subtle text-accent text-xs`
- Theme toggle: `btn-icon`, sun or moon icon `18px`
- User avatar: `32×32` circle, same as left rail, opens same account popover

***

## SCREEN 5: SIDEBAR — SOURCES PANEL

### Panel Structure

- Background: `bg-[#0a0b0f]`
- Full height: `100vh - 0` (no header offset — header is in chat panel)
- Border-right: `1px solid rgba(255,255,255,0.06)`


### Sidebar Header

- Padding: `16px 16px 8px`
- Notebook name echo: `sm font-semibold text-primary`, truncated 1 line
- Stats line: `xs text-muted` — `"N sources · M selected"`
- Action buttons row: `[+ Add] [🔍 Search]` — both `btn-icon 28×28`, right-aligned, gap-1


### Filter Bar

- Below header, `px-3 pb-2`
- Horizontal scrollable chip row: `All · PDF · YouTube · Web · Audio · Images · Text`
- Each chip: `xs px-3 py-1 rounded-full border`
- Active chip: `bg-accent-subtle border-accent/30 text-accent`
- Inactive: `bg-white/4 border-white/10 text-muted hover:text-secondary`


### Source List

- `overflow-y-auto` with styled scrollbar
- `padding: 0 8px 16px`
- Gap between items: `4px`

**Source Item Card (detailed):**

- Container: `rounded-xl p-3 bg-white/2 border border-white/6 cursor-pointer relative`
- Hover: `bg-white/4 border-white/10`, transition `instant`
- Layout: horizontal flex, `gap-3`, `align-items: flex-start`

**Source type icon (left):**

- `28×28px rounded-lg` box
- Each type gets unique bg color (all at 15% opacity, white icon):
    - PDF: `#ef4444/15` bg + red icon
    - DOCX: `#3b82f6/15` + blue
    - PPTX: `#f97316/15` + orange
    - XLSX/CSV: `#10b981/15` + green
    - YouTube: `#ef4444/15` + red
    - Web: `#06b6d4/15` + cyan
    - Audio/MP3: `#8b5cf6/15` + violet
    - Image: `#ec4899/15` + pink
    - Text paste: `rgba(255,255,255,0.08)` + gray

**Content (center, flex-1):**

- Filename: `sm font-medium text-primary`, truncated 1 line
- Second line: source type + chunk count: `xs text-muted` — `"PDF · 42 chunks"`

**Status indicator (right):**

- `completed`: `8px` circle, solid `#16a34a`, static
- `processing` / `embedding`: animated arc SVG, `16×16px`, `#4f6ef7` stroke
- `ocr_running` / `transcribing`: same arc but with amber `#d97706` stroke
- `failed`: `16×16px` badge with `!`, `bg-red/15 text-red-400 rounded-full`
- `pending`: `8px` circle, `rgba(255,255,255,0.20)`, pulse animation

**Selected state:**

- Left border: `3px solid #4f6ef7` (applied via `box-shadow: inset 3px 0 0 #4f6ef7` to avoid layout shift)
- Background: `rgba(79,110,247,0.08)`
- Border color: `rgba(79,110,247,0.25)`

**Hover-revealed kebab `[⋯]`:**

- Appears at `top: 8px right: 8px`, `btn-icon 24×24`
- Menu: `Rename · View Text · Delete`
- Delete: `text-red-400`

**Failed state expanded error:**

- Clicking failed item: a `rounded-lg bg-red/8 border border-red/20 p-2 mt-2` block slides down below the card content
- Content: `xs text-red-300` showing the error message from `material.error`
- A `[Retry]` ghost button at bottom-right of the error block

**Processing skeleton (when status is `pending` and just uploaded):**

- The entire card content area is replaced with shimmer lines
- The type icon area shows a gray shimmer square


### Select All / Deselect All

- Appears only when `materials.length > 0`
- Just below filter bar: `"Select all"` / `"Deselect all"` ghost link `xs text-accent hover:underline`, left-aligned


### Empty Sidebar State

- Centered in sidebar below header
- Upload icon (cloud with arrow, `48px`, `text-muted`)
- `"No sources yet"` `sm font-semibold text-primary`
- `"Upload files, paste URLs, or add text to get started"` `xs text-muted`, centered, `max-width: 180px`
- `[+ Add First Source]` primary button below

***

## SCREEN 6: ADD SOURCE — BOTTOM SHEET (Upload Dialog)

**Trigger:** `[+ Add]` button in sidebar header
**Behavior:** Slides up from the bottom of the sidebar panel, not a page-level modal

### Sheet Container

- Dimensions: `100% sidebar width × max 65vh`
- Background: `bg-[#0f1117] border border-white/10 rounded-t-2xl`
- Entrance: `translateY(100%) → translateY(0)` over `350ms ease-snap`
- Exit: `translateY(0) → translateY(100%)` over `250ms ease-out-expo`
- Drag handle: centered at top `4px × 32px`, `bg-white/15`, `border-radius: full`, `margin: 8px auto`
- Drag-to-dismiss: dragging down > 60px triggers exit animation


### Sheet Header

- `"Add Sources"` — `base font-semibold text-primary`, `16px left`
- `[✕]` btn-icon top-right
- Subtitle: `xs text-muted` — `"Upload files, paste a URL, or type your content"`


### Tab Bar

- 3 tabs: `"Files"` · `"URL"` · `"Text"`
- Container: `bg-white/5 rounded-xl p-1`, `mx-16px`
- Tab: `flex-1 text-center py-2 text-sm rounded-lg`
- Active: `bg-surface-raised shadow-sm text-primary font-medium`
- Inactive: `text-muted hover:text-secondary`
- Animated sliding pill under active tab


### Files Tab

**Drop zone:**

- `rounded-2xl border-2 border-dashed border-white/15 bg-white/2`
- Min-height: `120px`
- Center content: upload cloud icon `32px text-muted` + `"Drop files here or click to browse"` `sm text-secondary` + `"Max 25MB per file"` `xs text-muted`
- Drag-over state: `border-accent/50 bg-accent/4`, cloud icon scale-up `1.1`, border animates to solid
- Click: opens native file picker

**Supported formats strip:**

- Below drop zone, horizontal scrollable row of mini chips
- Each chip: file extension label `2xs font-mono bg-white/5 rounded px-1.5 py-0.5`
- Listed: `PDF DOCX PPTX XLSX CSV MP4 MP3 WAV PNG JPG`

**File Queue (after files selected):**

- Each file row: `rounded-lg bg-white/4 border border-white/8 px-3 py-2 flex items-center gap-2`
- Left: file type icon (16px, colored per type)
- Center: filename truncated + filesize `xs text-muted`
- Right: `[✕]` remove button `btn-icon 20×20`
- Entrance animation: `slide-in-right 150ms`
- During upload: a `2px` progress bar fills along the bottom of each row; color: accent blue
- Completed file: progress bar disappears, a green checkmark `fade-in` replaces the `[✕]` button
- Failed file: red border + error icon replaces checkmark

**Upload button:**

- Full-width, primary, `44px`, disabled until queue has files
- Label changes: `"Select files"` → `"Upload 3 files →"` → `"Uploading... (2/3)"` → `"Done ✓"`


### URL Tab

**URL input:**

- Full-width, standard input, placeholder `"Paste a URL, YouTube link, or web article..."`
- Auto-detection chip below (appears after 300ms debounce when URL is typed):
    - YouTube detected: `▶ YouTube video` — orange chip
    - Web page: `🌐 Web page` — blue chip
    - Unknown/invalid: `⚠ Could not detect type` — amber chip, fades after 2s

**Title input (optional):**

- Smaller, below URL input, `"Custom title (optional)"`

**Add button:** full-width primary `"Add as Source →"`

### Text Tab

**Title input:** standard input, `"Give it a title (optional)"`, full-width, at top
**Content textarea:**

- `min-height: 160px`, monospace font
- Placeholder: `"Paste your notes, article, or any text content..."`
- Character counter: `xs text-muted` bottom-right of textarea — `"N chars"`

**Add button:** full-width primary `"Add as Source →"`

***

## SCREEN 7: WEB SEARCH DIALOG (Web Research Panel)

**Trigger:** `[🔍 Search]` button in sidebar header
**Behavior:** Slides in from right over the sidebar (not a new page, not a center modal)

### Panel Container

- Dimensions: same width as sidebar (`280px`), full sidebar height
- Background: `bg-[#0f1117]`
- Entrance: `translateX(280px) → translateX(0)` over `300ms ease-snap`
- Overlays the source list (covers it), not a split


### Panel Header

- `[←]` chevron button (goes back to source list) + `"Web Research"` `base font-semibold text-primary`
- Subtitle: `xs text-muted "Find and add web content as sources"`


### Search Input

- Full-width, search icon inside left, auto-focused on open
- Placeholder: `"Search the web..."`
- `[Enter]` or search button triggers search


### Loading State

- 3 result card skeletons with shimmer
- A thin indeterminate shimmer bar below the search input while loading


### Results List

Each result card:

- `rounded-xl p-3 bg-white/3 border border-white/8`
- Top: favicon `16×16` rounded + domain `xs text-muted` — horizontal
- Title: `sm font-medium text-primary`, 2 lines max
- Snippet: `xs text-secondary`, 2 lines max
- Bottom: `[+ Add as Source]` ghost button, right-aligned
    - On click: button becomes `✓ Added` green chip (non-clickable), source animates into sidebar behind the panel


### Empty/No Results

- Centered: magnifier icon + `"No results found"` + `"Try different keywords"` `xs text-muted`


### Error State

- `"Search failed"` + `[Try Again]` button

***

## SCREEN 8: CHAT PANEL

### Panel Structure

- Background: `bg-[#07080c]`
- Top: header bar `48px` (described in Workspace Header)
- Below header: message history area `flex-1 overflow-y-auto`
- Bottom: floating composure bar


### Chat Session Bar (below header, above messages)

- Height: `40px`, `border-b border-white/6`
- Horizontal scrollable row of session chips inside: `px-4 py-2`
- Each session chip: `rounded-full bg-white/5 border border-white/8 px-3 py-1 text-xs text-secondary cursor-pointer`
- Active session: `bg-accent-subtle border-accent/30 text-accent`
- Hover: `bg-white/8 text-primary`
- Leftmost: `[+ New Chat]` chip — ghost/dashed border style
- Session names truncated at 16 chars with ellipsis
- Renaming: double-click on a session chip to inline-edit the name


### Message History Area

- Padding: `16px 20px`
- `padding-bottom: 100px` (space for floating composure bar)
- Scrolled to bottom on new message, smooth scroll
- Messages: `gap-4` between items

**Empty chat state (no messages):**

- Centered content block, vertically centered in the message area
- KeplerLab orbit icon `48px text-muted`
- `"Ask anything about your sources"` `xl font-semibold text-primary`
- `"Select sources in the sidebar, then start a conversation"` `sm text-secondary`
- Suggestion card grid: `2×2`, `gap-3`, `max-width: 560px`:
    - Each suggestion card: `rounded-xl bg-white/4 border border-white/8 p-4 cursor-pointer hover:bg-white/6 hover:border-white/15`
    - Small icon `16px text-accent` + suggestion text `sm text-secondary`
    - Examples: `"Summarize the key concepts"` · `"Create a study timeline"` · `"What are the main arguments?"` · `"Explain this like I'm a beginner"`
    - Clicking a card injects its text into the composure bar and auto-submits


### User Message Bubble

- Layout: right-aligned, `max-width: 72%`
- Container: `bg-white/8 border border-white/10 rounded-2xl rounded-br-xs px-4 py-3`
- Text: `base text-primary`
- Timestamp: `2xs text-muted`, appears only on hover of the message, positioned below-right
- If message has a slash command: a small colored command badge appears above the text (same as `CommandBadge` below)


### Assistant Message

- Layout: full-width (no bubble constraint)
- Top row: intent badge + timestamp
    - **Intent badge options:**
        - `[⬡ RAG]` — blue
        - `[⚙ Code]` — cyan
        - `[🔍 Research]` — orange
        - `[📊 Analysis]` — green
        - `[🧠 Agent]` — violet
    - Each: `bg-[color]/12 border border-[color]/25 text-[color] rounded-lg px-2 py-0.5 text-xs font-mono`
    - Timestamp: `2xs text-muted`, `ml-2`
- **Left accent line:** `2px solid rgba(79,110,247,0.25)` running down the full left side of the message, `margin-left: 0`, `padding-left: 16px`
- **Glowing orb at top of accent line:** `8px circle bg-accent rounded-full shadow-glow-blue`

**Message content rendering:**

- Markdown: headings, bold, italic, lists (bullet + numbered), blockquotes, horizontal rules
- Headings: `h1` → `xl font-semibold`, `h2` → `lg font-semibold`, `h3` → `base font-semibold`, all with `margin-top: 20px margin-bottom: 8px`
- Blockquote: `border-l-2 border-accent/30 pl-4 text-secondary italic`
- Code inline: `font-mono text-[#7dd3fc] bg-white/8 rounded px-1.5 py-0.5 text-xs`
- Code block: `bg-[#050608] rounded-xl border border-white/8 p-4 overflow-x-auto font-mono text-xs`
    - Language label: `xs text-muted` top-left inside the block
    - `[Copy]` button: `xs btn-secondary` top-right, appears on hover of the block, copies content to clipboard, changes to `[✓ Copied]` for 2s
- Tables: `w-full border-collapse`, `th` cells `bg-white/6 text-secondary text-left px-3 py-2 text-xs`, `td` cells `border-t border-white/6 px-3 py-2 text-sm`, alternating row tint `even:bg-white/2`
- Math (KaTeX): rendered in `bg-surface-sunken rounded-lg px-4 py-3 overflow-x-auto my-2`

**Citations (inline):**

- Footnote-style superscript `[1]` `[2]` etc. in `xs text-accent`
- Hovering: a floating card appears — `bg-surface-overlay border border-white/10 rounded-xl shadow-lg p-3 w-64`
    - Source material name `xs font-semibold`
    - Excerpt text `xs text-secondary`, `3 lines max`
    - Page/chunk reference if available `xs text-muted`

**Agent sub-components inside message (collapsible):**

- `AgentStepsPanel` — described below
- `AgentActionBlock` — described below
- `ExecutionPanel` — described below
- `ChartRenderer` — described below
- `GeneratedFileCard` — described below

**Message hover state:**

- `BlockHoverMenu` appears floating above top-right of the message — described below


### `AgentStepsPanel` (inside assistant message)

- Collapsible toggle: `"↳ Agent reasoning [N steps]"` `xs text-muted` with `[▾]` chevron, right side shows total elapsed time `xs text-muted font-mono`
- Expanded: vertical timeline
- Each step row: `flex gap-3 py-2 border-t border-white/4 first:border-0`
    - Left: `16px` circle indicator — `✓` green filled (done), spinning arc (current), empty circle gray (pending)
    - Center: step title `sm text-secondary`
    - Right: elapsed time `xs text-muted font-mono`
- Last step always shows `total elapsed` time in bold


### `AgentActionBlock` (inside message, expandable)

- Collapsed: header bar `bg-white/4 rounded-lg px-3 py-2` — action type badge + summary text + `[▾]` toggle
- Action type badges: same color system as intent badges
- Expanded: below header, `bg-[#050608] rounded-b-lg border border-white/8 p-3`
    - Content rendered by action type: code in monospace, search results as compact list, data in table


### `ResearchProgress` (inside streaming research response)

- Vertical timeline at the top of the response, before the report text
- Each step: `24px` icon circle + step name + detail (URL count or query text) + elapsed time
- Icons: 🔍 → 📄 → 🧠 → ✍ per research phase
- Active step: accent icon + pulsing ring around circle
- Completed: green checkmark icon


### `ExecutionPanel` (code execution results)

- Header bar `rounded-t-xl px-4 py-2.5 flex items-center justify-between`
    - Left: status — `●` dot (green=success, red=error) + `"Executed successfully"` or `"Execution failed"` `sm`
    - Right: elapsed time `xs font-mono text-muted`
- Output section: `bg-black/50 rounded-b-xl p-4 font-mono text-xs overflow-x-auto max-height: 300px overflow-y-auto`
    - stdout: `text-[#86efac]` (green)
    - stderr: `text-[#fca5a5]` (red), in a separate subsection with `"stderr:"` label above
- If `hasChart`: `ChartRenderer` renders below the output section


### `ChartRenderer` (data visualization)

- Container: `bg-[#0a0b0f] rounded-xl border border-white/8 p-4 mt-2`
- Title: `sm font-medium text-primary` above chart area
- Top-right (on container hover): `[⬇ PNG] [⬇ SVG]` ghost buttons `xs`
- Chart canvas area: `100% width, auto height`
- Empty/null data: `"Chart data unavailable"` centered with raw JSON in a collapsible code block


### `GeneratedFileCard` (downloadable file)

- `rounded-xl border border-white/8 bg-white/3 px-3 py-2.5 flex items-center gap-3`
- Hover: `border-white/18 bg-white/5`
- Left: `32×32 rounded-lg` file type icon bg:
    - CSV: `#10b981/15` green
    - Python `.py`: `#3b82f6/15` blue
    - JSON: `#f59e0b/15` amber
    - Other: `rgba(255,255,255,0.06)` gray
- Center: filename `sm font-medium` + filesize `xs text-muted`
- Right: `[⬇]` btn-icon, accent hover


### `DocumentPreview` (source material inline)

- Collapsible card: header row = document icon + `xs text-muted` source name + `[▾ Show]` toggle
- Expanded: `max-height: 160px overflow-y-auto bg-[#050608] rounded-b-lg p-3 font-mono text-xs text-secondary`
- Footer of expanded: `"Source: [material-title]"` `xs text-muted`


### `BlockHoverMenu` (floating on message hover)

- `bg-[#161820] border border-white/12 rounded-xl shadow-lg p-1 flex gap-0.5`
- Positioned: `absolute top: -40px right: 0`
- Entrance: `scale-in 120ms ease-snap` from bottom-right origin
- 4 icon buttons `28×28 btn-icon`:
    - 📋 Copy — copies message text
    - 🔖 Save — saves as note (placeholder)
    - 💬 Follow Up — opens `MiniBlockChat` below
    - ⋯ More — opens further options popover


### `MiniBlockChat` (follow-up within a block)

- `mt-2 bg-[#0f1117] border border-white/8 rounded-xl p-3`
- Header: `"Follow up"` `xs text-muted`
- Input: `bg-white/6 rounded-lg px-3 py-2 text-sm w-full` with `[→]` send icon inside right
- Response renders below input as a mini assistant message (same intent badge + content rendering, but smaller scale)
- Thread grows downward as more follow-ups are added


### `AgentThinkingBar` (streaming in-progress indicator)

- Floats inside the scroll area at the bottom of messages, above composure bar
- `bg-[#0f1117]/90 backdrop-blur-xl border border-white/8 rounded-xl px-4 py-2.5 mx-20px`
- Left: `16px` animated spinner (arc, `#4f6ef7`, `0.8s linear infinite`)
- Right: typewriter-cycling text — uses a queue of step descriptions, each one types in then holds for 1.2s:
    - `"Searching through your sources..."`
    - `"Reranking relevant chunks..."`
    - `"Synthesizing your answer..."`
- Entrance: `slide-up + fade-in 200ms`
- Exit: `fade-out + scale-out 150ms`


### Composure Bar (bottom, floating)

- Position: `absolute bottom: 16px left: 16px right: 16px`
- Container: `bg-[#0f1117]/95 backdrop-blur-2xl border border-white/12 rounded-3xl shadow-xl`
- Internal padding: `12px 12px 12px 16px`
- Layout: vertical stack

**Top area (slash command pills — only visible when command active):**

- `SlashCommandPills` floats inside the bar at top-left, before the textarea

**Middle area (main input row):**

- Left: active command badge (if any — detailed below)
- Center: `textarea` — auto-grows from `36px` (1 row) to `180px` (5 rows) then scrolls
    - Font: `base text-primary`, placeholder: `"Ask about your sources, or use / for commands..."`
    - No visible border (inherits bar)
    - Scrollbar styled (4px)
- Right side icons (vertical center):
    - Source indicator pill: shows `"N sources"` or `"All sources"` — `bg-white/6 rounded-full px-2.5 py-1 xs text-muted`, click opens a mini source picker dropdown
    - Voice input button: `btn-icon 32×32` microphone icon — active state: pulsing red background + waveform animation (5 animated bars)
    - Send button: `btn-icon 36×36 bg-accent rounded-xl` — accent filled — disabled (opacity 0.3) when input empty, enabled otherwise

**Source picker mini-dropdown (from source indicator click):**

- `bg-surface-overlay border border-white/10 rounded-2xl shadow-lg p-2 w-240px`
- Positions above the composure bar
- `"Select sources"` header `xs text-muted`
- List of sources with checkboxes (custom styled: `16×16 rounded-md border-white/20`, checked: `bg-accent border-accent`)
- `Select all` / `Deselect all` links at top

**`SlashCommandDropdown`:**

- Floats above composure bar (attached to bottom edge of a transparent overlay)
- `bg-[#0f1117]/96 backdrop-blur-xl border border-white/12 rounded-2xl shadow-[0_-8px_40px_rgba(0,0,0,0.5)]`
- `width: 320px`, max-height `320px`, scrollable
- Grouped sections with section labels `2xs text-muted uppercase letter-spacing: 0.08em`
    - **Generate:** `/flashcards` · `/quiz` · `/presentation` · `/mindmap`
    - **Analyze:** `/code` · `/analyze` · `/summarize`
    - **Research:** `/research` · `/search`
- Each item row: `flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/6`
    - Left: `/ ` + command name `sm font-mono text-accent`
    - Right: description `xs text-muted`
    - Far right: keyboard hint `2xs text-muted font-mono bg-white/6 rounded px-1.5 py-0.5`
- Active/highlighted item: `bg-white/8 text-primary`
- Entrance: `slide-up + fade-in 180ms ease-snap`

**`CommandBadge` (active command in composure bar):**

- `bg-accent/15 border border-accent/30 rounded-lg px-2 py-0.5`
- `/ [command]` in `xs font-mono text-accent`
- `[×]` remove button `12×12 text-muted hover:text-primary`, right side
- Entrance: `scale-in 150ms ease-bounce`

**`SuggestionDropdown` (contextual question chips):**

- Appears above composure bar when `partialInput.length ≥ 3`
- A horizontal scrollable strip of 4 suggestion chips
- Each: `bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-sm text-secondary cursor-pointer`
- Hover: `bg-accent/8 border-accent/25 text-accent`
- Left and right gradient fade overlays to hint scrollability

***

## SCREEN 9: STUDIO DRAWER

### Panel Structure

- Background: `bg-[#0a0b0f]`
- `border-left: 1px solid rgba(255,255,255,0.06)`
- Internal: `overflow-y-auto`, styled scrollbar


### Studio Header (top of drawer)

- `"Studio"` `base font-semibold text-primary`, `px-4 pt-4`
- Subtitle: `xs text-muted "Generate study materials"`


### Feature Launcher Grid

- `px-4 pt-3`
- `grid-template-columns: 1fr 1fr`, `gap-3`

**Feature Card (each):**

- `rounded-2xl p-4 bg-white/3 border border-white/6 cursor-pointer overflow-hidden relative`
- Hover: `bg-white/5 border-white/14 translateY(-1px) shadow-md`
- Transition: `standard (250ms)`
- Status pill (top-right corner if applicable): `[N saved]` green, `[Generating...]` amber pulsing

**Animated icon area (top, `48×48`):**

- Flashcards: CSS 3D card flip animation looping every 3s
- Quiz: bullseye icon with 3 concentric pulsing rings (CSS animation, staggered)
- Presentation: 3 layered slide rectangles in staggered 3D perspective, subtle depth offset
- Podcast: 5 vertical bars (equalizer waveform), each bar animates `scaleY` at staggered timing
- Mind Map: center dot + 3 orbiting dots connected by lines, rotating slowly
- Explainer Video: clapperboard icon, clap arm animates open-close every 2.5s

**Card text:**

- Feature name: `sm font-semibold text-primary`, below icon
- Description: `xs text-muted`, 1 line


### Generated Content Library (below feature grid)

- Collapsible section toggle: `"Saved Creations"` `xs text-muted font-medium` + `[▾]` chevron + count badge
- Content: compact list of saved items
- Each item: icon chip (feature color) + title truncated + date `xs text-muted` + `[▶ View]` ghost button right-aligned
- Empty: `xs text-muted "No saved content yet"` centered

***

## SCREEN 10: FLASHCARD VIEWER (Studio → Flashcards)

**Activation:** clicking the Flashcards feature card
**Layout:** overlays the Studio Drawer with a full-panel view (drawer content replaced)

### Header Bar

- `[←]` chevron (returns to Studio grid) + `"Flashcards"` `base font-semibold` + session stats `xs text-muted right-aligned "12 of 24"`
- Progress bar below header: thin `4px` fill bar, accent blue, animates on card change
- Circular arc progress widget (SVG): right side — `48×48`, shows percentage


### Config Toolbar (below progress bar)

- `[⚙ Configure]` ghost button — opens config sheet from bottom
- `[🔀 Shuffle]` ghost button — randomizes card order
- Session score chips: `Easy: N` green · `Medium: N` amber · `Hard: N` red


### Flashcard Stage

- Centered, `max-width: 680px`, `margin: 0 auto`
- Card container with 3D perspective: `perspective: 1200px`

**Card face (front and back):**

- `width: 100%, height: 320px`
- `bg-[#0f1117] border border-white/10 rounded-3xl shadow-xl`
- **Background texture per card:** a unique subtle gradient overlay determined by card index (5 preset: blue-tinted, violet-tinted, green-tinted, orange-tinted, neutral) at `5% opacity`
- Content: centered horizontally and vertically
- Front: question text `lg font-medium text-primary`, centered, `max-width: 80%`
- Back: answer text `base text-secondary`, centered, `max-width: 80%`; source citation chip below if available
- Card label: `2xs text-muted absolute top: 16px left: 20px` — `"QUESTION"` (front) / `"ANSWER"` (back)

**Flip mechanism:**

- CSS `transform: rotateY(180deg)`, `transform-style: preserve-3d`
- Front: `backface-visibility: hidden`
- Back: `transform: rotateY(180deg) backface-visibility: hidden`
- Animation: `400ms ease-snap`
- Trigger: clicking the card or pressing `Space`

**Flip hint (before first flip):**

- `"Click to reveal answer"` `xs text-muted` centered below card
- A subtle ripple animation on the card border to draw attention

**Difficulty buttons (visible only on back face):**

- Appear below card on flip, `slide-up + fade-in 200ms`
- 3 buttons in a row: `[✓ Easy] [≈ Medium] [✗ Hard]`
- Easy: `bg-green/12 border border-green/25 text-green-400 hover:bg-green/20`
- Medium: `bg-amber/12 border border-amber/25 text-amber-400`
- Hard: `bg-red/12 border border-red/25 text-red-400`
- Each: `rounded-xl px-6 py-2.5 sm font-medium`
- Clicking: card slides out right, next card slides in from right

**Navigation (below difficulty buttons or on front face):**

- `[←]` prev · card position indicator · `[→]` next
- Keyboard: `←/→` navigate, `Space` flip, `1/2/3` for Easy/Medium/Hard


### Session Complete State

- Card area transforms: scale-out animation, then a completion card appears
- Completion card: `bg-[#0f1117] rounded-3xl p-8 text-center`
- Large animated check circle `64px` drawing in (SVG stroke-dashoffset animation)
- `"Session Complete!"` `2xl font-semibold`
- Score breakdown: 3 large number + label pairs (Easy / Medium / Hard) in a row
- `[🔁 Retry Hard Cards]` secondary button + `[Start Over]` ghost button


### Flashcard Config Sheet (from `[⚙]` button)

- Bottom sheet, same entrance as upload dialog
- Source selector: scrollable material chips (removable)
- Count stepper: `[-] [20] [+]` with preset chips `10 ·

