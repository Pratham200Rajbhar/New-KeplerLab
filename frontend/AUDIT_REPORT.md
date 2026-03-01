# Frontend Audit Report

## Table of Contents
- [Part 1: Bugs, Errors, and Issues](#part-1-bugs-errors-and-issues)
- [Part 2: Hardcoded Colors](#part-2-hardcoded-colors)

---

## Part 1: Bugs, Errors, and Issues

### 1. ErrorBoundary.jsx — Undefined Tailwind Classes

| Line | Issue | Fix |
|------|-------|-----|
| 48 | `bg-surface-secondary` is not defined in `tailwind.config.js`. Class has no effect — details area renders with no background. | Change to `bg-surface-raised` or `bg-surface-overlay` (both are defined). |
| 59 | `bg-primary` and `hover:bg-primary/90` are not defined in `tailwind.config.js`. The "Try Again" button has no background color. | Change to `bg-accent hover:bg-accent-dark` (both are defined). |
| 66–67 | `bg-surface-secondary` and `hover:bg-surface-secondary/80` — same issue. "Reload Page" button has no background. | Change to `bg-surface-raised hover:bg-surface-overlay`. |

### 2. ExplainerDialog.jsx — Undefined Tailwind Classes

| Line | Issue | Fix |
|------|-------|-----|
| 253, 295, 317, 353 | `hover:border-border-hover` — `border-hover` is not a defined color in `tailwind.config.js`. Hover state does nothing. | Change to `hover:border-border-strong` (which is defined). |
| 409 | `bg-bg-secondary` — not defined. Progress bar track has no visible background. | Change to `bg-surface-raised` or `bg-surface-overlay`. |

### 3. StudioPanel.jsx — Undefined Tailwind Class

| Line | Issue | Fix |
|------|-------|-----|
| 594 | `hover:bg-bg-secondary` — not defined. Cancel button hover state invisible. | Change to `hover:bg-surface-raised`. |

### 4. HomePage.jsx, StudioPanel.jsx, PodcastPlayer.jsx — Invalid `hover:bg-glass-light`

| File | Lines | Issue | Fix |
|------|-------|-------|-----|
| HomePage.jsx | 157, 255 | `hover:bg-glass-light` — `glass-light` is a plain CSS class (`.glass-light`), not a Tailwind utility color. Tailwind's `hover:` prefix cannot target CSS classes. Hover does nothing. | Use `hover:bg-surface-raised` or add `glass-light` to tailwind.config.js as a custom color. |
| StudioPanel.jsx | 855, 864, 873, 1803 | Same issue. | Same fix. |
| PodcastPlayer.jsx | 195 | Same issue. | Same fix. |

### 5. App.jsx — Incomplete useEffect Dependencies (Workspace)

| Line | Issue | Fix |
|------|-------|-----|
| 80 | `useEffect` depends on `[id, currentNotebook?.id]` but uses `setCurrentNotebook`, `setDraftMode`, and `getNotebook` inside. While setters from `useContext` are stable, `getNotebook` (imported from API) is also stable, so this is technically correct but fragile. The real bug: when `id` and `currentNotebook?.id` haven't changed but network conditions cause a stale notebook, there's no way to re-fetch. | Add a comment explaining why deps are intentionally partial, or add `getNotebook` to deps for correctness. |

### 6. HomePage.jsx — Missing useEffect Dependency

| Line | Issue | Fix |
|------|-------|-----|
| ~55 | `useEffect(() => { loadNotebooks(); }, [])` — `loadNotebooks` is defined inside the component and closes over `setNotebooks`. If `loadNotebooks` reference changes on re-render, the effect doesn't re-run. | Either move `loadNotebooks` inside the effect, or add it to the dependency array with `useCallback`. |

### 7. ChatPanel.jsx — Suppressed Exhaustive-Deps

| Line | Issue | Fix |
|------|-------|-----|
| 198 | `// eslint-disable-line react-hooks/exhaustive-deps` — effect depends on `[currentNotebook?.id, draftMode]` but calls `loadSessions()` which closes over several state values. | Wrap `loadSessions` in `useCallback` with proper deps and include it in the effect deps. |

### 8. StudioPanel.jsx — Suppressed Exhaustive-Deps

| Line | Issue | Fix |
|------|-------|-----|
| 513 | `// eslint-disable-line react-hooks/exhaustive-deps` — effect for podcast phase changes. | Audit the missing dependencies and add them or extract into `useCallback`. |

### 9. MiniBlockChat.jsx — Suppressed Exhaustive-Deps

| Line | Issue | Fix |
|------|-------|-----|
| 34 | `// eslint-disable-next-line react-hooks/exhaustive-deps` — auto-run effect fires once on mount but may reference stale props. | Include `initialPrompt` and `onSend` or equivalent in deps array. |

### 10. useMindMap.js — Suppressed Exhaustive-Deps

| Line | Issue | Fix |
|------|-------|-----|
| 18 | `// eslint-disable-next-line react-hooks/exhaustive-deps` — effect for auto-generating mind map. | Audit and add the actual missing dependencies. |

### 11. StudioPanel.jsx (InlineExplainerView) — Stale Closure in useEffect Cleanup

| Line | Issue | Fix |
|------|-------|-----|
| 1750–1752 | Cleanup function references `videoBlobUrl` state variable, but the cleanup captures the value at the time the effect was created (always `null` on first render). When the component unmounts, `URL.revokeObjectURL(null)` is called — the actual blob URL is never revoked, causing a **memory leak**. | Use a ref to store the blob URL: `const blobUrlRef = useRef(null)`. In the `.then()`, set both `setVideoBlobUrl(blobUrl)` and `blobUrlRef.current = blobUrl`. In cleanup: `if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)`. |

### 12. AgentActionBlock.jsx (StepCard) — Dead Code

| Line | Issue | Fix |
|------|-------|-----|
| 61 | `const stdoutRef = { current: null };` is declared but never used anywhere in the component. It's also a plain object, not `useRef()`, so it would be recreated every render if it were used. | Remove the dead variable. |

### 13. SourceItem.jsx — Dark-Mode-Only Hardcoded Colors Break Light Mode

| Line | Issue | Fix |
|------|-------|-----|
| 225–226, 269, 279, 284, 294, 327 | All colors are hardcoded dark-mode hex values (`#2A2D35`, `#20222A`, `#3A3F4B`, `#4A4E58`). In light mode, these create dark patches on light backgrounds. The entire component is unusable in light theme. | Replace all hardcoded hex classes with design-system tokens: `bg-surface-raised`, `hover:bg-surface-overlay`, `border-border`, `border-border-strong`, `text-text-secondary`, `hover:text-text-primary`. |

### 14. WebSearchDialog.jsx — Dark-Mode-Only Hardcoded Colors

| Line | Issue | Fix |
|------|-------|-----|
| 111, 112, 170, 177, 222, 231, 243, 256, 273, 285, 286 | All hardcoded hex colors (`#2A2D35`, `#3A3F4B`, `#1C1E26`, `#2C3039`, `#4A4E58`) will look broken in light mode. Additionally uses default Tailwind colors (`text-gray-300`, `text-gray-400`, `text-gray-500`, `text-gray-600`, `bg-blue-600`) that don't follow the design system. | Replace with design-system tokens: `bg-surface-raised`, `bg-surface-overlay`, `border-border`, `text-text-secondary`, `text-text-muted`, `bg-accent`, etc. |

### 15. MindMapCanvas.jsx & MindMapNode.jsx — Entirely Hardcoded Dark Theme

| File | Lines | Issue | Fix |
|------|-------|-------|-----|
| MindMapCanvas.jsx | 138, 177, 195, 208, 218, 240, 254, 282–283, 310–314 | All inline styles use hardcoded dark colors (`#1a202c`, `#2d3748`, `#4a5568`). ReactFlow background, nodes, edges, controls — all dark-only. | Use CSS custom properties: `var(--surface)`, `var(--border)`, `var(--text-secondary)`, etc., or Tailwind classes where ReactFlow supports `className`. |
| MindMapNode.jsx | 5–7, 22, 36, 44, 50, 54, 71 | `depthColors` object and all inline styles use hardcoded hex values. Hover handlers set explicit `borderColor` values. | Create CSS-variable-based depth colors or use Tailwind's bg-surface-* tokens with opacity variants. |

### 16. FileViewerPage.jsx — Entirely Hardcoded Dark Theme

| Line | Issue | Fix |
|------|-------|-----|
| 57, 69, 80, 90, 102, 142, 157, 183, 259, 279, 298, 304, 324 | All hex colors (`#0F1117`, `#191B21`, `#1C1E26`, `#2A2D35`, `#3A3F4B`) and `text-gray-*` classes are dark-mode-only. Page is completely broken in light mode. | If the page is intentionally dark-only (standalone viewer), add `dark` class to root. Otherwise, migrate to design-system tokens. |

### 17. PresentationView.jsx — Self-Contained Inline Styles

| Line | Issue | Fix |
|------|-------|-----|
| 52–53, 250–550+ | The entire component uses a `<style>` tag with ~100 hardcoded color values. It's a self-contained dark presentation viewer and won't adapt to a light theme. | If light-mode support is needed, convert the `<style>` tag to use CSS custom properties. If intentionally dark-only, this is acceptable but should be documented. |

### 18. PresentationView.jsx — slides.map() Potential Key Issue

| Line | Issue | Fix |
|------|-------|-----|
| 587 | `slides.map((slide) => ...)` — uses `slide.id` as key which should be fine if IDs are unique. But if slides are generated without unique IDs, duplicates could cause rendering issues. | Verify that `slide.id` is always unique. Consider using index as fallback: `key={slide.id || i}`. |

### 19. ChatMessage.jsx — isInsidePre Ref Pattern (Not a Bug, but Fragile)

| Line | Issue | Fix |
|------|-------|-----|
| 14–37 | `isInsidePre` ref is used in ReactMarkdown `components` to detect block vs inline code. The pattern works but relies on ReactMarkdown's rendering order (pre before code). If ReactMarkdown's internal behavior changes, inline code won't render correctly. | Consider using a CSS-only approach or check for `node.position` in the AST instead. |

### 20. UploadDialog.jsx — Hardcoded Toast Colors

| Line | Issue | Fix |
|------|-------|-----|
| 499–501 | Toast notifications use hardcoded rgba/hex values in inline styles for error (red) and success (green) backgrounds, borders, and text. | Use design-system tokens: `var(--status-error)`, `var(--status-success)`, or Tailwind classes `bg-status-error/15`, `text-status-error`. |
| 518 | Loading overlay uses hardcoded `rgba(17,17,24,0.6)`. | Use `var(--backdrop)`. |

### 21. Sidebar.jsx — Minor Hardcoded Shadow

| Line | Issue | Fix |
|------|-------|-----|
| 420 | `shadow-[0_4px_20px_rgba(0,0,0,0.2)]` — hardcoded shadow in Tailwind arbitrary value. | Use `shadow-elevated` or `shadow-glass` (both defined in config). |

---

## Part 2: Hardcoded Colors

All hardcoded colors found in JSX component files (excluding index.css which defines the design system).

### ChatMessage.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 23 | `#1a1b26` | `customCodeTheme background` — inline style | `var(--surface-sunken)` or `var(--surface)` |

### ChatPanel.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 1173 | `#68d391` | `borderLeft: '3px solid #68d391'` — mind map banner | `var(--status-success)` or `var(--accent)` |
| 1174 | `#2d3748` | `background: '#2d3748'` — mind map banner | `var(--surface-raised)` |
| 1183 | `#a0aec0` | `color: '#a0aec0'` — banner text | `var(--text-secondary)` |
| 1184 | `#e2e8f0` | `color: '#e2e8f0'` — banner strong text | `var(--text-primary)` |
| 1191 | `#a0aec0` | `color: '#a0aec0'` — dismiss button | `var(--text-secondary)` |

### StudioPanel.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 722 | `#ef4444` (×3) | Error toast — `bg-[#ef4444]/10`, `border-[#ef4444]/30`, `bg-[#ef4444]/20` | `bg-status-error/10`, `border-status-error/30`, `bg-status-error/20` |
| 724 | `#ef4444` | SVG icon `text-[#ef4444]` | `text-status-error` |
| 729 | `#f87171` | Title `text-[#f87171]` | `text-status-error` (or add `status-error-light` to config) |
| 1456 | `rgba(0,0,0,0.07)`, `rgba(0,0,0,0.04)` | Flashcard `boxShadow` inline style | `shadow-glass-sm` (Tailwind class from config) |
| 1480 | `rgba(0,0,0,0.07)`, `rgba(0,0,0,0.04)` | Flashcard back `boxShadow` | Same as above |
| 1630 | `#10b981` (×3) | Quiz correct answer: `border-[#10b981]`, `bg-[#10b981]/10`, `rgba(16,185,129,0.15)` | `border-status-success`, `bg-status-success/10`, `shadow-[0_0_15px_var(--status-success)/15]` |
| 1632 | `#ef4444` (×2) | Quiz wrong answer: `border-[#ef4444]`, `bg-[#ef4444]/10` | `border-status-error`, `bg-status-error/10` |
| 1649 | `#10b981` | Correct icon badge `bg-[#10b981]` | `bg-status-success` |
| 1654 | `#ef4444` | Wrong icon badge `bg-[#ef4444]` | `bg-status-error` |
| 1665 | `#10b981` (×4) | Score banner correct: gradient, border, shadow | `from-status-success/10`, `to-status-success/5`, `border-status-success/30` |
| 1666 | `#ef4444` (×4) | Score banner wrong: gradient, border, shadow | `from-status-error/10`, `to-status-error/5`, `border-status-error/30` |
| 1669 | `#10b981` | Score text `text-[#10b981]` | `text-status-success` |
| 1679 | `#ef4444` | Score text `text-[#ef4444]` | `text-status-error` |

### AgentActionBlock.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 130 | `#1a1b26` | SyntaxHighlighter `background` inline style | `var(--surface-sunken)` or `var(--surface)` |

### MindMapCanvas.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 138 | `#4a5568` | Edge `stroke` style | `var(--border-strong)` |
| 177 | `#1a202c` | ReactFlow container `backgroundColor` | `var(--surface)` |
| 195 | `#1a202c` | Header `background` | `var(--surface)` |
| 208 | `#2d3748` | Header bottom `borderBottom` | `var(--border)` |
| 218 | `#4a5568` | Export button `border` | `var(--border-strong)` |
| 240 | `#4a5568` | Expand button `border` | `var(--border-strong)` |
| 254 | `#4a5568` | Collapse button `border` | `var(--border-strong)` |
| 282 | `#2d3748` | Results panel `background` | `var(--surface-raised)` |
| 283 | `#4a5568` | Results panel `border` | `var(--border-strong)` |
| 310 | `#4a5568` | MiniMap `nodeColor` prop | `var(--border-strong)` |
| 311 | `rgba(0,0,0,0.5)` | MiniMap `maskColor` prop | `var(--backdrop)` |
| 312 | `#2d3748` | MiniMap `background` style | `var(--surface-raised)` |
| 314 | `#4a5568` | Background dots `color` prop | `var(--border-strong)` |

### MindMapNode.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 5 | `#3d4f6b` | `depthColors[0]` | Use CSS vars or design tokens |
| 6 | `#2d4a3e` | `depthColors[1]` | Use CSS vars or design tokens |
| 7 | `#2d3748` | `depthColors[2]` | Use CSS vars or design tokens |
| 22 | `#252d3a` | Fallback `depthColors` | `var(--surface-raised)` |
| 36 | `#68d391`, `#4a5568` | Node `border` highlighted/normal | `var(--status-success)` / `var(--border-strong)` |
| 44 | `#68d391` | Highlighted node `boxShadow` | `var(--status-success)` |
| 50 | `#68d391` | Hover `borderColor` assignment | `var(--status-success)` |
| 54 | `#4a5568` | Mouse-leave `borderColor` | `var(--border-strong)` |
| 71 | `#4a5568` | Toggle button `background` | `var(--surface-overlay)` |
| 36,44 | `white` | Node text `color: 'white'` | `var(--text-primary)` |

### SourceItem.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 225 | `#2A2D35` | Checked state `bg-[#2A2D35]` | `bg-surface-raised` |
| 225 | `#20222A` | Unchecked hover `hover:bg-[#20222A]` | `hover:bg-surface-overlay` |
| 226 | `#2A2D35` | Processing `bg-[#2A2D35]/50` | `bg-surface-raised/50` |
| 269 | `#3A3F4B` | Menu button hover `hover:bg-[#3A3F4B]` | `hover:bg-surface-overlay` |
| 279 | `#20222A` | Dropdown bg `bg-[#20222A]` | `bg-surface-raised` |
| 279 | `#3A3F4B` | Dropdown border `border-[#3A3F4B]` | `border-border-strong` |
| 284, 294 | `#2A2D35` | Dropdown item hover `hover:bg-[#2A2D35]` | `hover:bg-surface-overlay` |
| 327 | `#4A4E58` | Checkbox border unchecked `border-[#4A4E58]` | `border-border-strong` |
| 269, 284, 294 | `gray-400`, `gray-300` | Tailwind default gray colors | `text-text-muted`, `text-text-secondary` |

### WebSearchDialog.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 111 | `#3A3F4B` | Divider border `border-[#3A3F4B]/50` | `border-border/50` |
| 112 | `#3A3F4B` | Section border `border-[#3A3F4B]/50` | `border-border/50` |
| 170 | `#2A2D35`, `#3A3F4B`, `#2C3039` | Result card bg/border/hover | `bg-surface-raised`, `border-border`, `hover:bg-surface-overlay` |
| 177 | `#4A4E58`, `#1C1E26` | Checkbox border/bg | `border-border-strong`, `bg-surface` |
| 222 | `#2A2D35`, `#1C1E26`, `#3A3F4B` | Preview panel gradient bg/border | `bg-surface-raised`, `border-border` |
| 231 | `#3A3F4B` | Favicon border | `border-border` |
| 243 | `#3A3F4B` | Section divider | `border-border` |
| 256, 273 | `#2A2D35`, `#3A3F4B` | Action buttons bg/border | `bg-surface-raised`, `border-border` |
| 285 | `#2A2D35`, `#3A3F4B` | Empty state bg/border | `bg-surface-raised/10`, `border-border` |
| 286 | `#2A2D35` | Empty state icon bg | `bg-surface-raised/40` |
| Various | `text-gray-300`, `text-gray-400`, `text-gray-500`, `text-gray-600` | Multiple elements | `text-text-secondary`, `text-text-muted` |
| Various | `bg-blue-600`, `bg-blue-500/10`, `border-blue-500/40`, `hover:bg-blue-600/20`, `hover:border-blue-500/50`, `hover:text-blue-300` | Blue accent colors | `bg-accent`, `bg-accent-subtle`, `border-accent-border`, `hover:bg-accent-light`, `text-accent` |

### FileViewerPage.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 57 | `#191B21`, `#2A2D35` | Header bg/border | `bg-surface`, `border-border` |
| 69, 80 | `#2A2D35` | Dividers | `bg-border` |
| 90, 102 | `#2A2D35` | Button hover bg | `hover:bg-surface-raised` |
| 142, 183 | `#2A2D35`, `#3A3F4B` | Action buttons bg/hover | `bg-surface-raised`, `hover:bg-surface-overlay` |
| 157 | `#2A2D35`, `#3A3F4B` | Error icon container | `bg-surface-raised`, `border-border` |
| 259 | `#0F1117` | Page background | `bg-surface` |
| 279, 298, 324 | `#0F1117` | Loading/error overlay bg | `bg-surface` |
| 304 | `#1C1E26`, `#2A2D35` | Info bar bg/border | `bg-surface-raised`, `border-border` |
| Various | `text-gray-200`, `text-gray-400`, `text-gray-500`, `text-gray-600` | Multiple elements | `text-text-primary`, `text-text-secondary`, `text-text-muted` |
| Various | `text-white` | Override text | `text-text-primary` (in dark mode, --text-primary is already white) |

### PresentationView.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 52 | `rgba(0,0,0,0.5)` | Container shadow | `var(--backdrop)` |
| 53 | `#000` | Container background | `var(--surface)` |
| 262 | `rgba(255,255,255,0.08)` | Slide card border (in `<style>`) | `var(--border)` |
| 266 | `rgba(0,0,0,0.25)` | Slide card shadow | `var(--shadow-glass)` |
| 284 | `rgba(26,29,46,0.5)` | Header bg | Should use CSS var |
| 285 | `rgba(255,255,255,0.05)` | Header bottom border | `var(--border-light)` |
| 314, 321, 325–326 | Multiple `rgba(...)` | Nav buttons, active state | Use CSS vars |
| 379, 381, 387 | Multiple | Context menu bg/border/shadow | Use CSS vars or design tokens |
| 393 | `rgba(99,102,241,0.9)` | Active context item | Use `var(--accent)` |
| 402–403 | `rgba(26,29,46,0.6)`, `rgba(255,255,255,0.06)` | Footer bg/border | Use CSS vars |
| 410–411, 422, 431 | Multiple `rgba(...)` | Slide counter, progress | Use CSS vars |
| 440 | `rgba(3,4,7,0.95)` | Overview panel bg | Use CSS var |
| 453, 465, 474, 476–477 | Multiple | Overview elements | Use CSS vars |
| 484–485 | `rgba(0,0,0,0.85)`, `rgba(255,255,255,0.95)` | Tooltip | Use CSS vars |
| 497, 501 | Multiple | Dropdown bg/shadow | Use CSS vars |
| 516, 524, 531, 533, 541, 543, 545 | Multiple | Dropdown items, dividers, empty state | Use CSS vars |
| 564 | `rgba(99,102,241,0.1)`, `#a5b4fc`, `rgba(99,102,241,0.2)` | Active button inline style | Use `var(--accent-subtle)`, `var(--accent)`, `var(--accent-muted)` |
| 632 | `rgba(255,255,255,0.4)` | Slide number color | `var(--text-muted)` |
| 680 | `rgba(99,102,241,0.2)`, `#a5b4fc`, `rgba(99,102,241,0.4)` | Download button active | Use accent CSS vars |
| 688 | `rgba(249,115,22,0.15)` | PPTX icon bg | Use `var(--status-warning)` with opacity |
| 698 | `rgba(16,185,129,0.15)` | HTML icon bg | Use `var(--status-success)` with opacity |
| 914 | `#f97316` | SVG stroke PPTX icon | `var(--status-warning)` |
| 920 | `#ef4444` | SVG stroke delete icon | `var(--status-error)` |
| 927, 934 | `#10b981` | SVG stroke HTML/download icons | `var(--status-success)` |

### UploadDialog.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 262 | `rgba(0,0,0,0.7)` | Backdrop (with fallback) | Already uses `var(--backdrop)` as primary — OK |
| 314 | `rgba(0,0,0,0.15)` | File card shadow | `shadow-glass-sm` or `var(--shadow-glass)` |
| 499 | `rgba(239,68,68,0.15)`, `rgba(34,197,94,0.15)` | Toast background | `var(--status-error)`, `var(--status-success)` with opacity |
| 500 | `rgba(239,68,68,0.3)`, `rgba(34,197,94,0.3)` | Toast border | Same with higher opacity |
| 501 | `#fca5a5`, `#86efac` | Toast text color | `var(--status-error)`, `var(--status-success)` |
| 518 | `rgba(17,17,24,0.6)` | Uploading overlay | `var(--backdrop)` |

### Sidebar.jsx

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 420 | `rgba(0,0,0,0.2)` | Upgrade card shadow (arbitrary Tailwind) | `shadow-elevated` (defined in config) |

### slashCommands.js (Used by SlashCommandDropdown, SlashCommandPills, CommandBadge)

| Line | Color | Context | Suggested Replacement |
|------|-------|---------|----------------------|
| 9 | `#f97316` | `/agent` command color | These are intentional brand colors for command identity. If theme-awareness is needed, map to CSS variables. Otherwise acceptable as semantic command colors. |
| 10 | `#3b82f6` | `/web` command color | Same |
| 11 | `#a855f7` | `/code` command color | Same |
| 12 | `#eab308` | `/data` command color | Same |
| 13 | `#22c55e` | `/quiz` command color | Same |
| 14 | `#14b8a6` | `/flash` command color | Same |
| 15 | `#ec4899` | `/summarize` command color | Same |
| 16 | `#6366f1` | `/mindmap` command color | Same |

---

## Summary

### Bugs that Cause Visible Breakage

| Priority | Issue | Affected Components |
|----------|-------|---------------------|
| **HIGH** | Undefined Tailwind classes (`bg-primary`, `bg-surface-secondary`, `border-border-hover`, `bg-bg-secondary`) — elements render with no bg/border | ErrorBoundary, ExplainerDialog, StudioPanel |
| **HIGH** | `hover:bg-glass-light` does nothing — `glass-light` is a CSS class, not a Tailwind color | HomePage, StudioPanel, PodcastPlayer |
| **HIGH** | Memory leak — blob URL never revoked due to stale closure in cleanup | StudioPanel (InlineExplainerView) |
| **MEDIUM** | Dark-mode-only hardcoded colors break light theme | SourceItem, WebSearchDialog, FileViewerPage, MindMapCanvas, MindMapNode |
| **LOW** | Suppressed eslint exhaustive-deps warnings (4 locations) | ChatPanel, StudioPanel, MiniBlockChat, useMindMap |
| **LOW** | Dead code (`stdoutRef`) | AgentActionBlock |

### Hardcoded Colors Count by File

| File | Count |
|------|-------|
| PresentationView.jsx | ~50+ |
| MindMapCanvas.jsx | ~14 |
| MindMapNode.jsx | ~11 |
| WebSearchDialog.jsx | ~25+ |
| FileViewerPage.jsx | ~18 |
| StudioPanel.jsx | ~20 |
| SourceItem.jsx | ~10 |
| ChatPanel.jsx | 5 |
| UploadDialog.jsx | 6 |
| slashCommands.js | 8 |
| ChatMessage.jsx | 1 |
| AgentActionBlock.jsx | 1 |
| Sidebar.jsx | 1 |
| **Total** | **~170+** |
