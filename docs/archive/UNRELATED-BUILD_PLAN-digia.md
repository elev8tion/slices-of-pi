# {{PROJECT_NAME}} — Master Build Plan

> **Source**: Extracted from `https://app.digia.tech/` (Flutter Web no-code builder)
> **Goal**: Local, solo-dev no-code builder for mobile apps + web pages + experiments
> **AI Co-pilot**: .pi agent (subagent integration)
> **Plan created**: 2026-06-16

---

## How To Use This Document

- Each phase has numbered tasks with clear **done conditions**.
- If we stop mid-phase, mark the last completed task and resume there.
- **Dependencies** between phases are explicit — don't skip a phase unless noted.
- **State files** (`.phase-*-state.md`) track where we left off.
- Tasks marked `[CHEATSHEET]` have a condensed reference at the end.

---

## Phase 0 — Sanitize & Scaffold

**Goal**: Strip all Digia identity, rename to your project name, scaffold the monorepo.

**Dependencies**: None (starts fresh from the extracted toolchest)
**Estimate**: 1 day

<!--- STATE: .phase-0-state.md --->

### 0.1 — Name the Project
- [ ] Decide on a project name (e.g., `forge-studio`, `kinetic-builder`, `hack-canvas`)
- [ ] Decide on short codes: `PROJECT_NAME`, `ProjectName`, `project-name`
- [ ] Write name to `PROJECT_NAME` file at repo root
- [ ] Update this document: replace all `{{PROJECT_NAME}}` with the real name

**Done when**: We have a name and it's written to a root-level file.

### 0.2 — Sanitize Toolchest Contents
- [ ] Run `sanitize-rename` skill on `~/digia-tech-toolchest/`
- [ ] Layer 0: Map all occurrences of `digia`, `Digia`, `DIGIA` in text files
- [ ] Layer 1: Replace in all `.md` `.json` `.yaml` `.html` `.txt` files
- [ ] Layer 2: Rename any files/directories containing old names
- [ ] Layer 3: Check binary assets (SVGs mention `digia` in paths — those need updating)
- [ ] Layer 4: Verify zero content hits remain
- [ ] Also strip: `digia-builder-dashboard-42470` → replace with placeholder
- [ ] Also strip: `app.digia.tech` → replace with `localhost:3001` or `localhost:8765`
- [ ] Also strip: all Google API keys (remove from source — user provides own)

**Done when**: `grep -rli "digia" ~/digia-tech-toolchest/` returns 0.

### 0.3 — Clean External References
- [ ] Remove Sentry DSN references (replaced with local logging)
- [ ] Remove PostHog API key references (stripped entirely)
- [ ] Remove Firebase project references (replaced with SQLite + local storage)
- [ ] Remove Tawk.to widget IDs (stripped entirely)
- [ ] Remove Paddle vendor references (stripped entirely)
- [ ] Remove SuprSend config (stripped entirely)
- [ ] Remove AppSumo references (stripped entirely)
- [ ] Remove Google OAuth client IDs (user provides own if needed)

**Done when**: No third-party SaaS identifiers remain in the toolchest.

### 0.4 — Scaffold Monorepo Structure
```
~/{{project-name}}/
├── README.md
├── PLAN.md                         ← This file (symlink or copy)
├── STATE.md                        ← Current phase/status overview
├── builder/                        ← Next.js frontend (visual builder)
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                ← Dashboard / project list
│   │   ├── editor/[projectId]/page.tsx
│   │   ├── playground/page.tsx
│   │   └── api/                    ← Next.js API routes / proxy
│   ├── components/
│   │   ├── canvas/                 ← Drag-drop canvas
│   │   ├── widgets/                ← Widget component registry
│   │   ├── panels/                 ← Property panel, palette, layers
│   │   └── ai/                     ← AI chat panel
│   ├── lib/
│   │   ├── widget-system/          ← Widget definitions & rendering
│   │   ├── code-generators/        ← Flutter/React code generators
│   │   └── pi-bridge/              ← .pi agent integration
│   └── public/
│       └── icons/                  ← Extracted SVG icons
├── backend/
│   ├── requirements.txt
│   ├── server.py                   ← FastAPI main
│   ├── models/                     ← SQLite models (one per entity)
│   ├── routes/                     ← API endpoint handlers
│   └── processors/                 ← Code gen, export logic
├── shared/
│   ├── types/                      ← Data model definitions
│   └── constants/                  ← Shared constants
└── experiments/                    ← Saved experiment files
```
- [ ] Create all directories
- [ ] Write root `README.md` with project overview and setup instructions
- [ ] Write root `STATE.md` with current phase tracking
- [ ] Initialize git repo at root

**Done when**: `tree ~/{{project-name}}` shows the full structure (files can be empty stubs).

### 0.5 — Import Extracted Knowledge
- [ ] Copy extracted API endpoints → `backend/routes/_contract-reference.md`
- [ ] Copy extracted data models → `shared/types/`
- [ ] Copy extracted widget palette → `builder/lib/widget-system/widget-catalog.md`
- [ ] Copy extracted analytics events → `shared/constants/analytics-events.md` (as reference for anti-patterns)
- [ ] Copy integration configs → `shared/constants/external-services.md` (documenting what was stripped)
- [ ] Copy SVGs → `builder/public/icons/`
- [ ] Link to original bundle for reference: `main.dart.js` path in README

**Done when**: Key extraction outputs are imported into the monorepo.

### 0.6 — Install Base Dependencies
- [ ] `npm create next-app@latest builder/` (or manual setup)
- [ ] `pip install fastapi uvicorn sqlite3` in backend/
- [ ] Verify both dev servers start
- [ ] `git add && git commit -m "phase-0: scaffold complete"`

**Done when**: `npm run dev` in builder/ and `python server.py` in backend/ both start without errors.

---

## Phase 1 — Core Builder MVP

**Goal**: Working visual page editor with 10 core widgets + Flutter code export.

**Dependencies**: Phase 0 complete
**Estimate**: 2-3 weeks

<!--- STATE: .phase-1-state.md --->

### 1.1 — Data Layer (Backend)

#### 1.1.1 — Project Model & CRUD
- [ ] Create `Project` SQLite model: id, name, slug, created_at, updated_at
- [ ] Implement `POST /api/projects` — create project
- [ ] Implement `GET /api/projects` — list all projects
- [ ] Implement `GET /api/projects/:id` — get single project
- [ ] Implement `PATCH /api/projects/:id` — update project
- [ ] Implement `DELETE /api/projects/:id` — soft delete project
- [ ] Implement `POST /api/projects/:id/duplicate` — clone project

**Verify**: `curl` CRUD cycle works on all project endpoints.

#### 1.1.2 — Page Model & CRUD
- [ ] Create `Page` model: id, project_id (FK), name, slug, sort_order, config (JSON)
- [ ] Implement `POST /api/pages` — add page to project
- [ ] Implement `GET /api/projects/:id/pages` — list project pages
- [ ] Implement `PATCH /api/pages/:id` — update page
- [ ] Implement `DELETE /api/pages/:id` — delete page
- [ ] Implement `POST /api/pages/:id/duplicate` — duplicate page

**Verify**: Can create a project, add 3 pages, reorder them, delete one.

#### 1.1.3 — Widget State Storage
- [ ] Create `WidgetNode` model: id, page_id (FK), type, props (JSON), parent_id, sort_order
- [ ] Implement `GET /api/pages/:id/widgets` — get full widget tree for page
- [ ] Implement `POST /api/pages/:id/widgets` — add widget to page
- [ ] Implement `PATCH /api/widgets/:id` — update widget props
- [ ] Implement `DELETE /api/widgets/:id` — delete widget
- [ ] Implement `POST /api/widgets/:id/move` — reorder/reparent widget

**Verify**: Can build a widget tree, update props, reorder, delete — tree persists on page reload.

#### 1.1.4 — Health & Utility
- [ ] `GET /api/health` — server status
- [ ] Request logging middleware
- [ ] Error response format: `{ error: string, details?: any }`
- [ ] CORS middleware for frontend dev server

**Verify**: `curl localhost:8765/api/health` returns 200.

### 1.2 — Widget System Definition

#### 1.2.1 — Widget Registry Architecture
- [ ] Define `WidgetDefinition` interface:
  ```typescript
  interface WidgetDefinition {
    type: string;
    category: 'layout' | 'display' | 'input' | 'media' | 'navigation' | 'custom';
    name: string;
    description: string;
    icon: string;  // path to SVG
    props: PropDef[];
    defaultProps: Record<string, any>;
    canHaveChildren: boolean;
    renderPreview: (props: any, children: WidgetNode[]) => JSX.Element;
    generateFlutter: (props: any, children: WidgetNode[], context: GenContext) => string;
    generateReact: (props: any, children: WidgetNode[], context: GenContext) => string;
  }
  ```
- [ ] Define `PropDef` interface: key, label, type (text|number|color|boolean|select|image|icon), defaultValue, options
- [ ] Build registry with `registerWidget(widget)` and `getWidget(type)` methods
- [ ] Build category-indexed lookup

**Verify**: Registry loads all 10 base widgets, typescript compiles.

#### 1.2.2 — Core Widgets (10 Base)

**Layout** (start here — everything nests inside these):
- [ ] **Container** — padding, margin, bg color, border, alignment, width, height
- [ ] **Row** — horizontal flex, main/cross axis alignment, gap
- [ ] **Column** — vertical flex, main/cross axis alignment, gap
- [ ] **Stack** — absolute positioning, z-order

**Display** (content widgets):
- [ ] **Text** — content, font size, weight, color, alignment, font family
- [ ] **Image** — src (URL or upload), fit, width, height, border radius
- [ ] **Icon** — icon name, size, color

**Input** (interactive widgets — stubbed for MVP):
- [ ] **Button** — label, onTap (placeholder), color, rounded
- [ ] **TextField** — label, placeholder, input type, validation

**Scroll/List**:
- [ ] **ListView** — children, scroll direction, item spacing

**Done when**: All 10 widgets have definition files in `builder/lib/widget-system/widgets/` with type, props, defaultProps, canHaveChildren, icon, and at least `renderPreview` implemented.

### 1.3 — Editor Canvas (Frontend)

#### 1.3.1 — Canvas Component
- [ ] Render live preview of the widget tree using `renderPreview` functions
- [ ] Maintain widget tree state (flat array with parentId references → build tree)
- [ ] Sync widget tree with backend on changes (debounced auto-save)
- [ ] Render frame/device mockup (phone outline for mobile, full width for web)
- [ ] Highlight selected widget with border/overlay
- [ ] Show widget type labels on hover

**Verify**: Can display a Column > [Text, Image, Button] tree rendered as preview.

#### 1.3.2 — Drag-Drop from Palette
- [ ] Widget palette sidebar (scrollable list of all widget types by category)
- [ ] Drag widget from palette → drop onto canvas
- [ ] Drop zone indicators (highlight valid parent on hover)
- [ ] Auto-select new widget after drop
- [ ] Logical drop targets: layout widgets accept children, display/input don't

**Verify**: Drag 5 widgets onto canvas, see them render in a tree.

#### 1.3.3 — Selection & Reorder
- [ ] Click to select widget (highlight + show property panel)
- [ ] Drag to reorder children within same parent (swap animation)
- [ ] Keyboard: arrow keys to navigate widget tree, Delete to remove
- [ ] Right-click context menu: duplicate, delete, move up/down, wrap in Container
- [ ] Multi-select with Shift+Click (batch delete, batch move)

**Verify**: Click a Text → property panel shows. Drag it below the Button. Delete it.

#### 1.3.4 — Widget Tree / Layers Panel
- [ ] Tree view of all widgets in the page (hierarchical, indented)
- [ ] Click tree item → select widget on canvas
- [ ] Drag tree item to reparent
- [ ] Eye icon to toggle visibility
- [ ] Lock icon to prevent selection

**Verify**: Tree shows Column > [Row > [Text, Icon], Button]. Drag Text into Row → tree updates, canvas updates.

### 1.4 — Property Panel

#### 1.4.1 — Property Rendering
- [ ] When widget selected, render property controls based on `PropDef`
- [ ] Text input for `text`, `number`, `url` types
- [ ] Color picker for `color` type
- [ ] Toggle/switch for `boolean` type
- [ ] Dropdown for `select` type
- [ ] Slider for numeric ranges
- [ ] Collapsible sections: Layout, Style, Content, Advanced
- [ ] Changes reflect instantly on canvas
- [ ] Debounced save to backend

**Verify**: Change Text widget's font size → canvas updates immediately. Reload page → value persists.

#### 1.4.2 — Style Shortcuts
- [ ] Quick style toolbar: bold, italic, underline, alignment, text color, bg color
- [ ] Padding/margin editors with visual indicators on canvas
- [ ] Border radius controls
- [ ] Width/height toggles: auto, fill, fixed, wrap content

**Verify**: Set padding on Container → canvas shows padding spacing.

### 1.5 — Flutter Code Export

#### 1.5.1 — Code Generator Architecture
- [ ] `generateFlutter()` on each widget → returns Dart code string
- [ ] Import management: collect unique imports from widget tree
- [ ] Indentation management (2-space, proper nesting)
- [ ] Widget tree traversal: depth-first, parent wraps children
- [ ] Props → Dart constructor arguments mapping

**Verify**: Simple Column > [Text("Hello"), Button("Click")] generates valid Dart.

#### 1.5.2 — Flutter Export Endpoint
- [ ] `POST /api/projects/:id/export/flutter` — generate full Flutter project
- [ ] Generate `pubspec.yaml` with required dependencies
- [ ] Generate `main.dart` with MaterialApp setup
- [ ] Generate one page per page in the project
- [ ] Generate `lib/` structure: screens/, widgets/, theme/
- [ ] Return zip file download

**Verify**: Export a 3-page project → unzip → `flutter build` passes.

#### 1.5.3 — Manual Flutter Project Template
- [ ] Static template files: `pubspec.yaml`, `android/`, `ios/`, `web/`
- [ ] Theme file with extracted color/style defaults
- [ ] Router setup for multi-page navigation
- [ ] Asset placeholder directories

**Verify**: Fresh export compiles with `flutter pub get && flutter build web --no-tree-shake-icons`

### 1.6 — Project Dashboard

- [ ] Grid of project cards with name, last modified, thumbnail
- [ ] Empty state: "Create your first project" with sample template
- [ ] Create project dialog: name + optional template select
- [ ] Delete confirmation dialog
- [ ] Click card → open editor
- [ ] Sort by: last modified, name, created date
- [ ] Search/filter by name

**Verify**: Create 3 projects, see them in grid, open one in editor.

### 1.7 — Integration & Polish

- [ ] Wire frontend API client to backend (use `fetch`, centralized in `/lib/api.ts`)
- [ ] Auto-save widgets after 2s of inactivity
- [ ] Unsaved changes indicator (dot on tab, confirm before navigate away)
- [ ] Toast notifications for save/error states
- [ ] Loading states for API calls
- [ ] Error boundaries for canvas rendering

**Verify**: Full cycle: create project → add 3 pages → build 10-widget page → preview → export → Flutter project compiles.

---

## Phase 2 — .pi Agent Co-pilot

**Goal**: AI can build and edit pages via natural language.

**Dependencies**: Phase 1 complete (editor exists to act on)
**Estimate**: 1 week

<!--- STATE: .phase-2-state.md --->

### 2.1 — AI Bridge Architecture

- [ ] Define agent tool interface:
  - `create_project(name)` → project_id
  - `add_page(project_id, name)` → page_id
  - `add_widget(page_id, type, parent_id, props)` → widget_id
  - `update_widget(widget_id, props)` → void
  - `delete_widget(widget_id)` → void
  - `reorder_widget(widget_id, new_parent_id, index)` → void
  - `get_page_state(page_id)` → full widget tree
  - `export_project(project_id, format)` → download URL
- [ ] Implement backend endpoint: `POST /api/ai/act` — receives action, executes, returns result
- [ ] Implement backend endpoint: `POST /api/ai/plan` — receives prompt, returns planned actions for confirmation
- [ ] Security: agent can only operate on the single user's projects (no auth needed — local only)

**Verify**: `curl -X POST localhost:8765/api/ai/act -d '{"action":"create_project","args":{"name":"Test"}}'` returns a project ID.

### 2.2 — Frontend AI Chat Panel

- [ ] Chat panel in editor (slide-in from right, overlay)
- [ ] Message bubble UI: user messages + agent responses
- [ ] Agent messages include: action summary + "Applied" / "Preview changes" buttons
- [ ] Stream agent responses (SSE from backend)
- [ ] Context: agent always knows the current page state (widget tree sent with each prompt)
- [ ] Suggested prompts: "Add a login form", "Change the primary color to blue", "What can I build?"

**Verify**: "Add a text widget that says Hello World" → widget appears on canvas.

### 2.3 — .pi Agent Integration

- [ ] Backend AI endpoint spawns a .pi subagent using `subagent()` tool
- [ ] Subagent receives: current widget tree as context + user's natural language prompt
- [ ] Subagent has access to the `act` tools defined in 2.1
- [ ] Subagent response format: `{ actions_taken: [...], summary: "...", widget_tree_snapshot: {...} }`
- [ ] Fallback: if no .pi agent available, use a local LLM (ollama, LM Studio, etc.)
- [ ] Environment variable: `PI_AGENT_ENABLED=true|false` (off by default, opt-in)

**Verify**: With `PI_AGENT_ENABLED=true`, typing "Make a login page with email and password fields and a submit button" creates 5+ widgets.

### 2.4 — Prompt Templates

- [ ] "Add a [widget_type] to the [parent_location]"
- [ ] "Change the [property] of [widget] to [value]"
- [ ] "Create a [page_type] page" (login, profile, settings, product list, etc.)
- [ ] "Style the page with [color_scheme] theme"
- [ ] "Arrange these widgets in a [layout_pattern]" (row, column, grid, stack)
- [ ] "Export this as [flutter/react]"
- [ ] "What's wrong with this page?" → agent audits the widget tree

**Verify**: Each template produces correct action sequences.

---

## Phase 3 — Web Page Builder + React Export

**Goal**: Same builder targets React/Next.js web pages.

**Dependencies**: Phase 1 complete (editor + widget system exist)
**Estimate**: 1-2 weeks

<!--- STATE: .phase-3-state.md --->

### 3.1 — React Code Generator

- [ ] Implement `generateReact()` for each of the 10 base widgets
- [ ] Generate valid JSX with Tailwind CSS classes (or CSS modules)
- [ ] Import management: collect imports from widget tree
- [ ] Component tree structure: one component per page
- [ ] State management: React hooks for form inputs, state containers
- [ ] Stub interactive behavior with comments

**Verify**: Column > [Text("Hello"), Button("Click")] generates valid React component.

### 3.2 — Web-Specific Widgets

- [ ] **Link** — href, target, text, style
- [ ] **NavBar** — logo, nav items, responsive hamburger menu
- [ ] **Form** — form wrapper, validation, submit handler
- [ ] **Section** — full-width section with bg, padding, max-width
- [ ] **Footer** — links, copyright, social icons
- [ ] **Video Embed** — YouTube/Vimeo iframe
- [ ] **Map** — embed map component
- [ ] **Card** — image, title, description, CTA button composition

**Verify**: Web-specific widgets render in preview and generate valid React code.

### 3.3 — Responsive Preview

- [ ] Viewport switcher: mobile (375×812), tablet (768×1024), desktop (1280×800)
- [ ] Responsive property system: widget can have different props per breakpoint
- [ ] Breakpoints visual indicator (colored bars at top of canvas)
- [ ] Preview renders at selected viewport size

**Verify**: Set button width to 100% on mobile and 50% on desktop → preview shows correct widths per breakpoint.

### 3.4 — React Export Endpoint

- [ ] `POST /api/projects/:id/export/react` — generate React project
- [ ] Generate `package.json` with React, Tailwind dependencies
- [ ] Generate component files in `src/components/`
- [ ] Generate pages in `src/pages/` (or `src/app/` for Next.js)
- [ ] Generate tailwind.config.js with extracted color theme
- [ ] Return zip file download

**Verify**: Export → unzip → `npm install && npm run build` passes.

### 3.5 — HTML (Standalone) Export

- [ ] `POST /api/projects/:id/export/html` — generate single HTML file
- [ ] Inline CSS (no external deps)
- [ ] Inline SVG icons
- [ ] Responsive via CSS media queries
- [ ] Self-contained: opens directly in browser

**Verify**: Exported HTML opens in browser with no errors, responsive across viewports.

---

## Phase 4 — Experiment Playground

**Goal**: Sandbox for widget experimentation with live coding and meta-mode.

**Dependencies**: Phase 1 complete (widget system exists to play with)
**Estimate**: 1 week

<!--- STATE: .phase-4-state.md --->

### 4.1 — Playground Canvas

- [ ] Empty canvas + "What do you want to build?" prompt (uses .pi agent)
- [ ] All 10+ widgets available from palette
- [ ] Split-pane: canvas + live code viewer
- [ ] Code viewer shows the Flutter/React code generated in real-time
- [ ] Copy code button
- [ ] Save experiment with name + description

**Verify**: Drag widgets onto playground canvas → code viewer updates in real-time.

### 4.2 — Widget Variant Testing

- [ ] Select a widget → "Create variant" → duplicates with different props
- [ ] Side-by-side comparison view (2-up, 3-up, 4-up grid)
- [ ] Variant labels showing the differing props
- [ ] "Select best" button that replaces original with chosen variant
- [ ] Export comparison as HTML report

**Verify**: Button with 3 variants (blue, green, red) shows side-by-side, select green → original updates.

### 4.3 — Live Code Override

- [ ] Monaco Editor panel (loaded from CDN) to edit generated code
- [ ] Changes re-render canvas in real-time
- [ ] "Save as override" persists custom code over widget's generated code
- [ ] "Revert to generated" clears override
- [ ] Syntax highlighting, error markers

**Verify**: Edit generated code in Monaco, canvas updates. Save override, reload, override persists.

### 4.4 — Meta Mode

- [ ] Playground can load the builder's own widget definitions
- [ ] Edit a widget definition's `renderPreview`, `generateFlutter`, or `generateReact`
- [ ] Changes take effect immediately in the builder itself
- [ ] "Publish widget update" → saves modified definition
- [ ] Version history of widget definitions

**Verify**: Edit Button widget's default color to purple → new buttons in builder are purple.

### 4.5 — Experiment Library

- [ ] List saved experiments with name, date, preview thumbnail
- [ ] Categorize: widget tests, layout tests, full page prototypes
- [ ] Share experiment as JSON export
- [ ] Import experiment JSON
- [ ] Duplicate experiment

**Verify**: Save experiment, close, reopen → all widgets and code overrides restored.

---

## Phase 5 — Full Widget System

**Goal**: All 35+ widget types from Digia extraction implemented.

**Dependencies**: Phase 1 (widget system), Phase 3 for web-specific
**Estimate**: 1-2 weeks

<!--- STATE: .phase-5-state.md --->

### 5.1 — Layout Widgets (complete)
- [ ] **Flex** — direction, wrap, alignment, flex values per child
- [ ] **Wrap** — wrap direction, spacing per line, run alignment
- [ ] **SafeArea** — insets handling
- [ ] **SizedBox** — exact width/height
- [ ] **Expandable** — expand/collapse with header
- [ ] **Overlay** — full-screen overlay with dismiss
- [ ] **Conditional Builder** — if/else visibility based on state
- [ ] **Scaffold** — full page structure (appBar, body, bottomNav, drawer, fab)

**Verify**: Each widget renders in preview and generates valid Flutter code.

### 5.2 — Input Widgets (complete)
- [ ] **Switch** — on/off toggle, active/inactive colors, label
- [ ] **Slider** — min, max, step, divisions, value label
- [ ] **RangeSlider** — min, max, lower/upper values
- [ ] **Calendar** — date picker, min/max date, first day of week
- [ ] **PinField** — OTP/pin input, length, obscure
- [ ] **Timer** — countdown/stopwatch, start/stop/reset actions

**Verify**: Input widgets work in preview (visual feedback, no backend required).

### 5.3 — Media Widgets (complete)
- [ ] **VideoPlayer** — URL source, controls, autoplay, loop
- [ ] **YouTube Player** — video ID, autoplay, controls visibility
- [ ] **Lottie Animation** — JSON source URL, autoplay, loop, repeats
- [ ] **WebView** — URL source, JS enabled, scroll
- [ ] **HtmlView** — render HTML string, base URL for assets
- [ ] **Markdown** — render markdown string, GitHub-flavored

**Verify**: Media widgets render preview (YouTube iframe works, Lottie loads from URL).

### 5.4 — Navigation Widgets
- [ ] **TabBar** — tab items, active tab indicator
- [ ] **TabController** — programmatic tab switching
- [ ] **TabViewContent** — content per tab

**Verify**: Tabs switch content on click.

### 5.5 — Data Widgets
- [ ] **FutureBuilder** — async data source, loading/error/data states
- [ ] **StreamBuilder** — real-time stream, initial data, connection state
- [ ] **PaginatedListView** — load more on scroll, page size, has more flag

**Verify**: Data widgets show loading → data states in preview with mock data.

### 5.6 — Custom Widget System
- [ ] User can compose multiple widgets → save as "Custom Widget"
- [ ] Custom widgets appear in palette under "Custom" category
- [ ] Custom widgets accept props (defined by user)
- [ ] Custom widgets can be edited/updated
- [ ] Import/export custom widgets as JSON

**Verify**: Compose Card = Container > [Image, Column > [Text(title), Text(description), Button]] → save as custom widget → drag onto another page.

---

## Phase 6 — Polish & Ship

**Goal**: Production-ready local tool.

**Dependencies**: All prior phases
**Estimate**: 1 week

<!--- STATE: .phase-6-state.md --->

### 6.1 — Performance
- [ ] Canvas uses virtual scrolling for large widget trees (500+ widgets)
- [ ] Debounced auto-save (2s debounce)
- [ ] Widget rendering memoization (React.memo for preview components)
- [ ] Image lazy loading in preview
- [ ] Bundle size optimization for frontend
- [ ] Backend request caching for repeated exports

### 6.2 — Error Handling
- [ ] Backend errors return structured JSON: `{ error: string, code: string, details?: any }`
- [ ] Frontend shows toast notifications for all errors
- [ ] Canvas error boundary catches rendering crashes without losing editor state
- [ ] Export validation: show warnings for unsupported widget combinations
- [ ] Auto-save recovery: if browser crashes, prompt to restore on reload

### 6.3 — Data Persistence
- [ ] Projects saved to SQLite `~/.{{project-name}}/data.db`
- [ ] Auto-backup on every page save to `~/.{{project-name}}/backups/`
- [ ] Export all projects as JSON file (full backup)
- [ ] Import projects from JSON backup file
- [ ] Version snapshots: auto-save version history of each page (last 50 versions)

### 6.4 — Developer Experience
- [ ] One-command start: `./start.sh` or `npm run dev` (starts both frontend + backend)
- [ ] Hot reload for widget definition changes
- [ ] `.env` file for configuration: port, db path, AI provider
- [ ] `README.md` with complete setup guide, architecture diagram, widget development guide
- [ ] Example projects shipped with the tool

### 6.5 — Documentation
- [ ] Complete README with project overview
- [ ] Widget development guide (how to add a new widget type)
- [ ] Code generator guide (how to add a new output target)
- [ ] .pi agent integration guide
- [ ] Architecture diagram (Mermaid)
- [ ] CHANGELOG.md

---

## Phase 7 — Stretch Goals (Optional)

**Not planned for initial build — revisit after Phases 0-6 are stable.**

- [ ] **Multi-user / Collaboration** — local network sharing, WebSocket sync
- [ ] **VS Code Extension** — edit .{{project-name}} projects from VS Code
- [ ] **Plugin System** — third-party widget packages
- [ ] **Drag-from-URL** — import design from Figma/any URL
- [ ] **Template Marketplace** — community templates
- [ ] **Publish to GitHub** — direct GitHub export
- [ ] **AI Design Generation** — "Build me a Shopify store front" → full project
- [ ] **Component Library** — pre-built screens (login, profile, settings, product list)
- [ ] **Theme Builder** — visual theme editor with live preview
- [ ] **Data Binding** — connect widgets to data sources visually
- [ ] **Backend Function Editor** — Monaco-based serverless function editor

---

## What We Strip vs. What We Keep

### Stripped Completely (SaaS Cruft)
| Feature | Why |
|---------|-----|
| Firebase Auth | Local-only, no users |
| Firebase Analytics | Removed |
| Firebase Storage | Replaced with local file system |
| Sentry Error Tracking | Terminal logs instead |
| PostHog Analytics | Removed entirely |
| Tawk.to Chat | Solo dev doesn't need live chat |
| Paddle Payments | Free local tool |
| SuprSend Notifications | Removed |
| AppSumo Integration | Not applicable |
| App Store Publishing | Replaced with code export |
| Team/Collaboration | Solo dev mode |
| Workspace/Org Management | Single workspace |
| Usage Credits/Limits | Unlimited local use |
| Onboarding Wizard | Removed (single user knows the tool) |
| Google Sign-In | No auth needed |

### Kept & Adapted (Core Pipeline)
| Feature | How It Changes |
|---------|----------------|
| Widget System | Expanded to multi-target (Flutter + React + HTML) |
| Page Editor | Same visual drag-drop, improved UX |
| Property Panel | Same concept, richer controls |
| Component System | Same + custom widget composition |
| Data Sources | Local JSON/API only |
| Version/Branching | Simplified to file snapshots |
| AI Assistant | Replaced with .pi agent subagent |
| Style System | Same + responsive per breakpoint |
| Preview Mode | In-browser (no APK build) |
| Asset Management | Local file system |

### New (Not in Digia)
| Feature | Where |
|---------|-------|
| .pi agent co-pilot | Phase 2 |
| Web Page Builder (React export) | Phase 3 |
| HTML Standalone Export | Phase 3 |
| Experiment Playground | Phase 4 |
| Live Code Override (Monaco) | Phase 4 |
| Meta Mode (builder self-editing) | Phase 4 |
| Widget Variant Testing | Phase 4 |
| Multi-Target Code Generation | Phase 1/3 |
| Responsive Breakpoints | Phase 3 |
| Custom Widget System | Phase 5 |

---

## Architecture Diagrams

### Data Flow
```
User Action → Frontend State → Debounced Save → Backend API → SQLite
                                                     ↓
                                              Code Generator
                                                     ↓
                                         Flutter / React / HTML
```

### Component Tree (Frontend)
```
App
├── Dashboard
│   ├── ProjectGrid
│   ├── CreateProjectDialog
│   └── EmptyState
└── Editor
    ├── AppBar (file name, save status, export button, preview toggle)
    ├── WidgetPalette (sidebar, left)
    │   ├── LayoutCategory
    │   ├── DisplayCategory
    │   ├── InputCategory
    │   └── CustomCategory
    ├── Canvas (center)
    │   ├── DeviceFrame
    │   ├── DropZone
    │   ├── WidgetPreview (recursive, one per widget node)
    │   └── SelectionOverlay
    ├── PropertyPanel (sidebar, right)
    │   ├── StyleSection
    │   ├── ContentSection
    │   ├── LayoutSection
    │   └── AdvancedSection
    ├── LayersPanel (tab, bottom or left)
    │   └── TreeView
    └── AIPanel (tab, right)
        ├── ChatMessages
        ├── PromptInput
        └── SuggestedPrompts
```

### API Route Map
```
GET    /api/health
POST   /api/projects                    → create
GET    /api/projects                    → list
GET    /api/projects/:id               → get
PATCH  /api/projects/:id               → update
DELETE /api/projects/:id               → soft delete
POST   /api/projects/:id/duplicate     → clone
POST   /api/projects/:id/export/flutter  → Flutter zip
POST   /api/projects/:id/export/react    → React zip
POST   /api/projects/:id/export/html     → HTML file

POST   /api/projects/:id/pages         → add page
GET    /api/projects/:id/pages         → list pages

GET    /api/pages/:id                  → get page
PATCH  /api/pages/:id                  → update page
DELETE /api/pages/:id                  → delete page
POST   /api/pages/:id/duplicate       → duplicate page
GET    /api/pages/:id/widgets          → get widget tree

POST   /api/pages/:id/widgets         → add widget
PATCH  /api/widgets/:id               → update widget
DELETE /api/widgets/:id               → delete widget
POST   /api/widgets/:id/move          → reorder

POST   /api/ai/plan                   → plan from prompt
POST   /api/ai/act                    → execute action
POST   /api/ai/stream                 → streaming co-pilot

POST   /api/experiments               → save experiment
GET    /api/experiments               → list experiments
GET    /api/experiments/:id           → get experiment
DELETE /api/experiments/:id           → delete experiment
```

---

## CHEATSHEET: Quick Reference

### Directory Commands
```bash
# Create project root
mkdir -p ~/{{project-name}}/{builder/{app/{editor,playground,api},components/{canvas,widgets,panels,ai},lib/{widget-system,code-generators,pi-bridge},public/icons},backend/{models,routes,processors},shared/{types,constants},experiments}

# Initialize
cd ~/{{project-name}} && git init
```

### Sanitize Commands
```bash
# Find all occurrences
grep -rli "digia\|Digia\|DIGIA" ~/digia-tech-toolchest/
grep -rli "digia-builder-dashboard-42470" ~/digia-tech-toolchest/
grep -rli "app\.digia\.tech" ~/digia-tech-toolchest/
grep -rli "AIzaSy" ~/digia-tech-toolchest/

# Replace in non-binary files
find ~/digia-tech-toolchest -type f \( -name '*.md' -o -name '*.json' \) \
  -exec sed -i '' 's/digia/{{project-name}}/g' {} +
```

### Widget Definition Template
```typescript
import { WidgetDefinition } from '../registry';

export const TextWidget: WidgetDefinition = {
  type: 'Text',
  category: 'display',
  name: 'Text',
  description: 'A text label with rich styling',
  icon: '/icons/text.svg',
  canHaveChildren: false,
  props: [
    { key: 'content', label: 'Content', type: 'text', defaultValue: 'Text' },
    { key: 'fontSize', label: 'Font Size', type: 'number', defaultValue: 16 },
    { key: 'fontWeight', label: 'Weight', type: 'select',
      options: ['normal','bold','w100','w200','w300','w400','w500','w600','w700','w800','w900'],
      defaultValue: 'normal' },
    { key: 'color', label: 'Color', type: 'color', defaultValue: '#000000' },
    { key: 'textAlign', label: 'Alignment', type: 'select',
      options: ['left','center','right','justify'], defaultValue: 'left' },
  ],
  defaultProps: { content: 'Text', fontSize: 16, fontWeight: 'normal', color: '#000000', textAlign: 'left' },
  renderPreview: (props) => <span style={{ fontSize: props.fontSize, fontWeight: props.fontWeight, color: props.color, textAlign: props.textAlign }}>{props.content}</span>,
  generateFlutter: (props) => `Text('${props.content}', style: TextStyle(fontSize: ${props.fontSize}, fontWeight: FontWeight.${props.fontWeight}, color: Color(0xFF${props.color.slice(1)})))`,
  generateReact: (props) => `<span style={{fontSize:${props.fontSize},fontWeight:'${props.fontWeight}',color:'${props.color}'}}>${props.content}</span>`,
};
```

### .env Template
```bash
# Server
PORT=8765
DB_PATH=~/.{{project-name}}/data.db

# AI Co-pilot
PI_AGENT_ENABLED=false
PI_MODEL=deepseek-chat
PI_BASE_URL=https://api.deepseek.com/v1
PI_API_KEY=

# Optional: Local LLM fallback
OLLAMA_ENABLED=false
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Verification Checklist (After Each Phase)
```bash
# Phase 0
grep -rli "digia" ~/{{project-name}}/          # → 0
npm run dev  # in builder/                      # → starts
python backend/server.py                        # → starts

# Phase 1
curl localhost:8765/api/health                  # → 200
# Create a project, add pages, build widgets → save → reload → still there
# Export Flutter → unzip → flutter pub get passes

# Phase 2
curl -X POST localhost:8765/api/ai/plan -d '...'  # → action plan
# Chat panel works, agent can add widgets

# Phase 3
# Export React → npm install && npm run build passes
# Export HTML → opens in browser

# Phase 4
# Drag widgets in playground → code updates in real-time
# Edit code in Monaco → canvas updates

# Phase 5
# All 35+ widgets render in preview
# All 35+ widgets generate valid Flutter code

# Phase 6
# One-command start works
# Backup/restore cycle works
```

---

## Phase State Tracking

Copy this section to `STATE.md` at the project root and update as we go.

```
# {{PROJECT_NAME}} — Build State

## Current Phase: Phase 0 — Sanitize & Scaffold
## Status: Not Started

## Progress
| Phase | Status | Started | Completed | Notes |
|-------|--------|---------|-----------|-------|
| 0 — Sanitize & Scaffold | Not Started | — | — | |
| 1 — Core Builder MVP | Not Started | — | — | |
| 2 — .pi Agent Co-pilot | Not Started | — | — | |
| 3 — Web Page Builder | Not Started | — | — | |
| 4 — Experiment Playground | Not Started | — | — | |
| 5 — Full Widget System | Not Started | — | — | |
| 6 — Polish & Ship | Not Started | — | — | |
| 7 — Stretch Goals | Not Started | — | — | |

## Last Active Task
None

## Blockers
None

## Notes
-
```
