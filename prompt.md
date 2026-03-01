I am working on a full-stack AI educational platform called KeplerLab AI Notebook.

TECH STACK:
- Backend: FastAPI (Python 3.11), Prisma ORM, PostgreSQL, LangChain, Pydantic v2
- Frontend: React 19, Vite, Tailwind CSS, AppContext for global state
- Auth: JWT Bearer token, get_current_user FastAPI dependency

---

## TASK: Add a Mind Map feature to this project.

Before writing any code, read these existing files to understand patterns:
- backend/app/routes/quiz.py (route pattern, auth, run_in_executor)
- backend/app/services/quiz/generator.py (how material text is read, how get_llm_structured is called)
- backend/app/services/ppt/generator.py (how GeneratedContent is saved via Prisma upsert)
- frontend/src/api/generation.js (fetch wrapper pattern)
- frontend/src/context/AppContext.jsx (global state shape)
- frontend/src/components/StudioPanel.jsx (how tabs are structured)
- frontend/src/components/ChatPanel.jsx (input area and useEffect patterns)

Follow every pattern you see in those files exactly. Do not invent new patterns.

---

## BACKEND — Create these files:

### FILE 1: backend/app/prompts/mindmap_prompt.txt
Content:
You are an expert knowledge mapping assistant.
Analyze the material text provided and generate a complete, exhaustive mind map.
You decide all nodes, all depth levels, all branches. There are absolutely no limits.
There must be exactly ONE root node with parent_id set to null.
Every other node must have a valid parent_id pointing to another node's id.
Use UUID strings for all id fields.
The question_hint for every node must be a complete, specific, standalone question
suitable for a RAG chatbot — not just the node label repeated.
Example question_hint for label "Proof of Work":
"Explain how Proof of Work (PoW) functions as a consensus mechanism in blockchain,
including its computational process, energy implications, and role in preventing double-spending."

Return ONLY valid JSON. No explanation. No markdown. No code blocks.
Structure:
{
  "title": "main topic",
  "nodes": [
    {
      "id": "uuid",
      "label": "short concept name",
      "parent_id": "parent uuid or null",
      "description": "1-2 sentence explanation",
      "question_hint": "full detailed question"
    }
  ]
}

Material text:
{material_text}

---

### FILE 2: backend/app/models/mindmap_schemas.py
Pydantic v2 models:

MindMapNode: id(str), label(str), parent_id(Optional[str]=None),
             description(str), question_hint(str), has_children(bool=False)

MindMapRequest: notebook_id(str), material_ids(List[str])

MindMapResponse: id(str), title(str), notebook_id(str), material_ids(List[str]),
                 nodes(List[MindMapNode]), created_at(datetime)

---

### FILE 3: backend/app/services/mindmap/__init__.py
Empty file.

### FILE 4: backend/app/services/mindmap/generator.py
Async function generate_mindmap(material_ids, notebook_id, user_id):

1. Read material text for each material_id using storage_service
   (same import and call as quiz generator)
2. Concatenate all texts with "\n\n"
3. Load mindmap_prompt.txt, replace {material_text} placeholder
4. Call get_llm_structured() at temperature=0.1 with MindMapResponse schema
   (same import and call pattern as quiz generator)
5. Post-process: build set of all parent_id values, set has_children=True
   on every node whose id appears in that set
6. Upsert into GeneratedContent via Prisma:
   contentType="mindmap", data=full response as dict,
   materialIds=material_ids, notebookId=notebook_id, userId=user_id
   Use upsert so regenerating overwrites existing row.
   (same Prisma upsert pattern as ppt generator)
7. Return MindMapResponse

---

### FILE 5: backend/app/routes/mindmap.py
APIRouter with three endpoints:

POST /
  Body: MindMapRequest
  Auth: get_current_user dependency
  Verify notebook belongs to user (same Prisma check as quiz route)
  Call generate_mindmap via run_in_executor (same as quiz route)
  Return: MindMapResponse

GET /{notebook_id}
  Auth: get_current_user dependency
  Query GeneratedContent where notebookId=notebook_id AND
  contentType="mindmap" AND userId=current_user.id
  If not found: raise HTTPException(404)
  Return: MindMapResponse deserialized from data field

DELETE /{id}
  Auth: get_current_user dependency
  Delete GeneratedContent record, verify userId matches
  Return: {"success": True}

---

### MODIFY: backend/app/main.py
Import mindmap_router and register:
app.include_router(mindmap_router, prefix="/mindmap", tags=["mindmap"])
Place right after the ppt_router line.

---

## FRONTEND — Create these files:

### FILE 6: frontend/src/api/mindmap.js
Follow generation.js pattern exactly. Three functions:
- generateMindMap({ notebookId, materialIds }) → POST /mindmap
  body: { notebook_id: notebookId, material_ids: materialIds }
- getMindMap(notebookId) → GET /mindmap/{notebookId}
- deleteMindMap(id) → DELETE /mindmap/{id}

---

### FILE 7: frontend/src/hooks/useMindMap.js
Custom hook receiving { notebookId, selectedSources }.

State: status("idle"|"checking"|"generating"|"ready"|"error"),
       mapData(null or response), isCanvasOpen(false), errorMessage(null)

On mount and when selectedSources changes, run this flow:
1. Set status="checking"
2. Call getMindMap(notebookId)
3. If 200: sort and compare response.material_ids vs selectedSources.
   If match → mapData=response, status="ready", done.
   If no match (stale) → go to step 4.
4. If 404 or stale: status="generating",
   call generateMindMap({ notebookId, materialIds: selectedSources }),
   on success → mapData=response, status="ready",
   on error → status="error", errorMessage=error.message

Expose: regenerate(), openCanvas(), closeCanvas() plus all state fields.

---

### FILE 8: frontend/src/components/MindMapNode.jsx
Custom React Flow node component. Props: { data, id }

data contains: label, question_hint, has_children, collapsedNodes(Set),
               onToggle(fn), onNodeLabelClick(fn), highlightedIds(Set), depth(number)

Layout: horizontal flex row.

Label area (left):
- bg by depth: 0=#3d4f6b, 1=#2d4a3e, 2=#2d3748, 3+=#252d3a
- border: 1px solid #4a5568, border-radius: 6px, padding: 8px 12px
- text: white 13px font-weight 500, cursor pointer
- hover: border-color #68d391
- if id in highlightedIds: bright green ring
- if highlightedIds not empty AND id not in it: opacity 0.3
- onClick: data.onNodeLabelClick(id, data.question_hint, data.label)

Toggle button (right, only if data.has_children=true):
- 20x20px, bg #4a5568, border-radius 4px, no border, white text 11px
- margin-left 6px, cursor pointer
- shows ">" if collapsedNodes.has(id) (children hidden)
- shows "<" if NOT collapsedNodes.has(id) (children visible)
- onClick: stopPropagation, then data.onToggle(id)

React Flow Handles:
- Target handle on LEFT (Position.Left), opacity 0
- Source handle on RIGHT (Position.Right), opacity 0

---

### FILE 9: frontend/src/components/MindMapCanvas.jsx

Install packages: @xyflow/react, dagre, html-to-image

Props: { mapData, onClose, onRegenerate }

Renders as fullscreen overlay: position fixed, inset 0, z-index 50, bg #1a202c

TOOLBAR (height 50px, flex row, border-bottom 1px solid #2d3748):
Left: [✕ Close] → onClose()
Center: mapData.title (white text)
Right: [🔄 Regen] → onRegenerate(), [📤 Export PNG] → html-to-image download,
       [🔍] text input → updates searchQuery state

Internal state: collapsedNodes = new Set(), searchQuery = ""

DAGRE LAYOUT (compute once on mount):
- import dagre, create new dagre.graphlib.Graph()
- setGraph({ rankdir:"LR", nodesep:60, ranksep:120 })
- add all nodes (width:160, height:40)
- add all edges (parent_id relationships)
- run dagre.layout(graph)
- extract x/y positions for each node

DEPTH FUNCTION: getDepth(nodeId) — walk parent_id chain, count steps from root

CHILDREN MAP: { nodeId: [childId...] } built from nodes array

getAllDescendants(nodeId): recursively collect all descendant IDs

toggleCollapse(nodeId):
  copy collapsedNodes set
  if has nodeId → delete it (expand)
  else → add nodeId + getAllDescendants(nodeId) (collapse)
  setCollapsedNodes(new copy)

onNodeLabelClick(nodeId, questionHint, nodeLabel):
  get setPendingChatMessage from AppContext
  call setPendingChatMessage({ text:questionHint, source:"mindmap", nodeLabel })
  call onClose()

visibleNodes (useMemo): exclude nodes where any ancestor is in collapsedNodes
visibleEdges (useMemo): exclude edges where source or target not in visibleNodes
highlightedIds (useMemo): Set of node IDs matching searchQuery (case insensitive)

React Flow setup:
- nodeTypes={{ mindMapNode: MindMapNode }}
- nodes = visibleNodes, each node.data includes collapsedNodes, onToggle,
  onNodeLabelClick, highlightedIds, depth
- edges = visibleEdges, type "smoothstep", stroke #4a5568
- fitView=true
- Include: Controls, MiniMap (bottom right), Background (dots)

---

### FILE 10: frontend/src/components/MindMapView.jsx
Props: { notebookId, selectedSources }

Uses useMindMap hook. Renders a card matching StudioPanel card styling.

Header always: "🗺 Mind Map"

Body by status:
- "checking": text "Checking saved map..."
- "generating": Tailwind animate-pulse skeleton suggesting horizontal tree
  (left wide rect → middle medium rects → right small rects)
  + text "Analyzing materials and building concept graph..."
- "ready" (canvas closed):
  Green ✅ badge in header
  Blurred area (blur-sm): "{mapData.nodes.length} concepts mapped"
  Centered: "👆 Click to Open"
  Entire card: cursor-pointer, onClick → openCanvas()
- "error":
  Error message text + [Retry] button → regenerate()

When isCanvasOpen=true: render <MindMapCanvas mapData={mapData}
  onClose={closeCanvas} onRegenerate={regenerate} />

---

## MODIFY THESE EXISTING FILES:

### MODIFY: frontend/src/context/AppContext.jsx
Find existing useState declarations. Add:
  const [pendingChatMessage, setPendingChatMessage] = useState(null)
Add both to the context value object.
Change nothing else.

### MODIFY: frontend/src/components/StudioPanel.jsx
Add "Mind Map" as the LAST tab (same style as other tabs, icon 🗺).
In the tab content conditional, add case for Mind Map tab:
  <MindMapView notebookId={currentNotebook?.id} selectedSources={selectedSources} />
Import MindMapView at top.
Change nothing else.

### MODIFY: frontend/src/components/ChatPanel.jsx
Add to AppContext destructure: pendingChatMessage, setPendingChatMessage
Add local state: const [mindMapBanner, setMindMapBanner] = useState(null)

Add useEffect:
  watches [pendingChatMessage]
  if pendingChatMessage?.source === "mindmap":
    setInputValue(pendingChatMessage.text)
    setMindMapBanner(pendingChatMessage.nodeLabel)
    inputRef.current?.focus()
    setPendingChatMessage(null)

In JSX, above the chat input box, add:
  {mindMapBanner && (
    <div with green left border, dark bg, small text>
      "Asking about: {mindMapBanner}"
      <button onClick={() => setMindMapBanner(null)}>✕</button>
    </div>
  )}
Change nothing else.

---

## STRICT RULES:
1. Read the existing files listed at the top BEFORE writing any code.
   Copy patterns exactly — do not invent new ones.
2. No new database tables. Reuse GeneratedContent model only.
3. No new React Router routes. Canvas is a fixed overlay.
4. LLM decides everything about the mind map. Zero node/depth limits anywhere.
5. Generation starts automatically on tab open. No generate button.
6. Stale detection: if saved map's material_ids differ from selectedSources,
   regenerate silently without prompting user.
7. Clicking a node label CLOSES the canvas and sends question to ChatPanel.
8. Reopening canvas is instant — data stays in hook state, no re-fetch.

Implement all files completely. Do not skip any file.
