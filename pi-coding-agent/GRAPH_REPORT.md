# Graph Report - /Users/kc/doc-kbs/pi-coding-agent/source  (2026-05-17)

## Corpus Check
- 30 files · ~132,840 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1117 nodes · 1156 edges · 60 communities (59 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_community-0|community-0]]
- [[_COMMUNITY_community-1|community-1]]
- [[_COMMUNITY_community-2|community-2]]
- [[_COMMUNITY_community-3|community-3]]
- [[_COMMUNITY_community-4|community-4]]
- [[_COMMUNITY_community-5|community-5]]
- [[_COMMUNITY_community-6|community-6]]
- [[_COMMUNITY_community-7|community-7]]
- [[_COMMUNITY_community-8|community-8]]
- [[_COMMUNITY_community-9|community-9]]
- [[_COMMUNITY_community-10|community-10]]
- [[_COMMUNITY_community-11|community-11]]
- [[_COMMUNITY_community-12|community-12]]
- [[_COMMUNITY_community-13|community-13]]
- [[_COMMUNITY_community-14|community-14]]
- [[_COMMUNITY_community-15|community-15]]
- [[_COMMUNITY_community-16|community-16]]
- [[_COMMUNITY_community-17|community-17]]
- [[_COMMUNITY_community-18|community-18]]
- [[_COMMUNITY_community-19|community-19]]
- [[_COMMUNITY_community-20|community-20]]
- [[_COMMUNITY_community-21|community-21]]
- [[_COMMUNITY_community-22|community-22]]
- [[_COMMUNITY_community-23|community-23]]
- [[_COMMUNITY_community-24|community-24]]
- [[_COMMUNITY_community-25|community-25]]
- [[_COMMUNITY_community-26|community-26]]
- [[_COMMUNITY_community-27|community-27]]
- [[_COMMUNITY_community-28|community-28]]
- [[_COMMUNITY_community-29|community-29]]
- [[_COMMUNITY_community-30|community-30]]
- [[_COMMUNITY_community-31|community-31]]
- [[_COMMUNITY_community-32|community-32]]
- [[_COMMUNITY_community-33|community-33]]
- [[_COMMUNITY_community-34|community-34]]
- [[_COMMUNITY_community-35|community-35]]
- [[_COMMUNITY_community-36|community-36]]
- [[_COMMUNITY_community-37|community-37]]
- [[_COMMUNITY_community-38|community-38]]
- [[_COMMUNITY_community-39|community-39]]
- [[_COMMUNITY_community-40|community-40]]
- [[_COMMUNITY_community-41|community-41]]
- [[_COMMUNITY_community-42|community-42]]
- [[_COMMUNITY_community-43|community-43]]
- [[_COMMUNITY_community-44|community-44]]
- [[_COMMUNITY_community-45|community-45]]
- [[_COMMUNITY_community-46|community-46]]
- [[_COMMUNITY_community-47|community-47]]
- [[_COMMUNITY_community-48|community-48]]
- [[_COMMUNITY_community-49|community-49]]
- [[_COMMUNITY_community-50|community-50]]
- [[_COMMUNITY_community-51|community-51]]
- [[_COMMUNITY_community-52|community-52]]
- [[_COMMUNITY_community-53|community-53]]
- [[_COMMUNITY_community-54|community-54]]
- [[_COMMUNITY_community-55|community-55]]
- [[_COMMUNITY_community-56|community-56]]
- [[_COMMUNITY_community-57|community-57]]
- [[_COMMUNITY_community-58|community-58]]
- [[_COMMUNITY_community-59|community-59]]

## God Nodes (most connected - your core abstractions)
1. `ExtensionAPI Methods` - 21 edges
2. `Extensions` - 16 edges
3. `TUI Components` - 16 edges
4. `All Settings` - 15 edges
5. `Options Reference` - 13 edges
6. `Custom Providers` - 12 edges
7. `ExtensionContext` - 12 edges
8. `All Actions` - 12 edges
9. `Custom Models` - 12 edges
10. `Events` - 12 edges
11. `Session File Format` - 12 edges
12. `CLI Reference` - 12 edges
13. `Commands` - 11 edges
14. `SDK` - 11 edges
15. `Entry Types` - 11 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities (60 total, 1 thin omitted)

### Community 0 - "community-0"
Cohesion: 0.05
Nodes (51): /compaction, /custom-provider, /../examples/extensions, /../examples/extensions/custom-provider-anthropic, /../examples/extensions/custom-provider-gitlab-duo, /../examples/extensions/dynamic-tools.ts, /../examples/extensions/github-issue-autocomplete.ts, /../examples/extensions/input-transform.ts (+43 more)

### Community 1 - "community-1"
Cohesion: 0.05
Nodes (41): API Types, Auth Header, code:typescript (import type { ExtensionAPI } from "@earendil-works/pi-coding), code:typescript (interface OAuthCredentials {), code:typescript (import {), code:typescript (// Text block), code:typescript (// Start tool call), code:typescript (output.usage.input = response.usage.input_tokens;) (+33 more)

### Community 2 - "community-2"
Cohesion: 0.05
Nodes (41): code:typescript (import { Type } from "typebox";), code:typescript (pi.sendMessage({), code:typescript (// Simple text message), code:typescript (pi.appendEntry("my-state", { count: 42 });), code:typescript (pi.setSessionName("Refactor auth module");), code:typescript (const name = pi.getSessionName();), code:typescript (// Set a label), code:typescript (pi.registerCommand("stats", {) (+33 more)

### Community 3 - "community-3"
Cohesion: 0.05
Nodes (40): Async factory functions, Available Imports, code:typescript (import type { ExtensionAPI } from "@earendil-works/pi-coding), code:bash (pi -e ./my-extension.ts), code:json ({), code:typescript (import type { ExtensionAPI } from "@earendil-works/pi-coding), code:typescript (pi.registerCommand("my-cmd", {), code:typescript (const parentSession = ctx.sessionManager.getSessionFile();) (+32 more)

### Community 4 - "community-4"
Cohesion: 0.05
Nodes (38): Agent and AgentState, AgentSession, code:typescript (import { AuthStorage, createAgentSession, ModelRegistry, Ses), code:typescript (// Access current state), code:typescript (session.subscribe((event) => {), code:bash (npm install @earendil-works/pi-coding-agent), code:typescript (import {), code:typescript (interface CreateAgentSessionResult {) (+30 more)

### Community 5 - "community-5"
Cohesion: 0.06
Nodes (34): /../../agent/src/types.ts, /../../ai/src/types.ts, /../examples/extensions/rpc-demo.ts, /../examples/rpc-extension-ui.ts, /../src/core/agent-session.ts, /../src/core/messages.ts, /../src/modes/rpc/rpc-client.ts, /../src/modes/rpc/rpc-types.ts (+26 more)

### Community 6 - "community-6"
Cohesion: 0.06
Nodes (33): /../examples/extensions/custom-compaction.ts, Branch Summarization, BranchSummaryEntry Structure, code:block1 (contextTokens > contextWindow - reserveTokens), code:typescript (import { convertToLlm, serializeConversation } from "@earend), code:typescript (pi.on("session_before_tree", async (event, ctx) => {), code:json ({), code:block2 (Before compaction:) (+25 more)

### Community 7 - "community-7"
Cohesion: 0.06
Nodes (31): /skills, code:json ({), code:yaml (description: Extracts text and tables from PDF files, fills ), code:yaml (description: Helps with PDFs.), code:block12 (brave-search/), code:`markdown (---), code:block14, code:block15 (+23 more)

### Community 8 - "community-8"
Cohesion: 0.06
Nodes (32): Anthropic Messages Compatibility, code:json ({), code:json ({), code:json ({), code:json ({), code:json ({), code:json ({), code:json ({) (+24 more)

### Community 9 - "community-9"
Cohesion: 0.06
Nodes (31): Amazon Bedrock, API Keys, Auth File, Azure OpenAI, Claude Pro/Max, Cloud Providers, Cloudflare AI Gateway, Cloudflare Workers AI (+23 more)

### Community 10 - "community-10"
Cohesion: 0.06
Nodes (31): All Settings, Branch Summary, code:json ({), code:json ({), code:json (// ~/.pi/agent/settings.json (global)), code:json ({), code:json ({), code:json ({) (+23 more)

### Community 11 - "community-11"
Cohesion: 0.07
Nodes (29): clone, code:json ({"type": "get_session_stats"}), code:json ({), code:json ({"type": "export_html"}), code:json ({"type": "export_html", "outputPath": "/tmp/session.html"}), code:json ({), code:json ({"type": "switch_session", "sessionPath": "/path/to/session.), code:json ({"type": "response", "command": "switch_session", "success":) (+21 more)

### Community 12 - "community-12"
Cohesion: 0.07
Nodes (29): agent_end, agent_start, auto_retry_start / auto_retry_end, code:json ({"type": "agent_start"}), code:json ({), code:json ({"type": "turn_start"}), code:json ({), code:json ({"type": "message_start", "message": {...}}) (+21 more)

### Community 13 - "community-13"
Cohesion: 0.07
Nodes (29): API Keys and OAuth, code:typescript (const { session } = await createAgentSession({), code:typescript (import { getModel } from "@earendil-works/pi-ai";), code:typescript (import { AuthStorage, ModelRegistry } from "@earendil-works/), code:typescript (import { createAgentSession, DefaultResourceLoader } from "@), code:typescript (import { createAgentSession } from "@earendil-works/pi-codin), code:typescript (import { createAgentSession, SessionManager } from "@earendi), code:typescript (import { Type } from "typebox";) (+21 more)

### Community 14 - "community-14"
Cohesion: 0.07
Nodes (28): CLI Reference, code:bash (pi -c                  # Continue most recent session), code:bash (pi [options] [@files...] [messages...]), code:bash (pi install <source> [-l]     # Install package, -l for proje), code:bash (cat README.md | pi -p "Summarize this text"), code:bash (pi --no-extensions -e ./my-extension.ts), code:bash (pi @prompt.md "Answer this"), code:bash (# Interactive with initial prompt) (+20 more)

### Community 15 - "community-15"
Cohesion: 0.07
Nodes (26): code:bash (pi install npm:@foo/bar@1.0.0), code:json ({), code:json ({), code:bash (pi -e npm:@foo/bar), code:block3 (npm:@scope/pkg@1.2.3), code:json ({), code:block5 (git:github.com/user/repo@v1), code:bash (# git@host:path shorthand (requires git: prefix)) (+18 more)

### Community 16 - "community-16"
Cohesion: 0.07
Nodes (27): Cancellation response (any dialog), code:json ({"type": "extension_ui_response", "id": "uuid-1", "value": "), code:json ({"type": "extension_ui_response", "id": "uuid-2", "confirmed), code:json ({"type": "extension_ui_response", "id": "uuid-3", "cancelled), code:json ({), code:json ({), code:json ({), code:json ({) (+19 more)

### Community 17 - "community-17"
Cohesion: 0.08
Nodes (26): Best Practices, code:typescript (import { withFileMutationQueue } from "@earendil-works/pi-co), code:typescript (import { Type } from "typebox";), code:typescript (// Correct: throw to signal an error), code:typescript (pi.registerTool({), code:bash (# Extension's read tool replaces built-in read), code:bash (# No built-in tools, only extension tools), code:typescript (import { createReadTool, createBashTool, type ReadOperations) (+18 more)

### Community 18 - "community-18"
Cohesion: 0.08
Nodes (26): 256-Color Palette, Backgrounds & Content (11 colors), Bash Mode (1 color), code:json ({), code:bash (mkdir -p ~/.pi/agent/themes), code:json ({), code:json ({), code:json ({) (+18 more)

### Community 19 - "community-19"
Cohesion: 0.08
Nodes (23): Autocomplete Providers, code:typescript (// Select from options), code:typescript (// Dialog shows "Title (5s)" → "Title (4s)" → ... → auto-dis), code:typescript (const controller = new AbortController();), code:typescript (// Status in footer (persistent until cleared)), code:typescript (pi.on("session_start", (_event, ctx) => {), code:typescript (import { Text, Component } from "@earendil-works/pi-tui";), code:typescript (import { CustomEditor, type ExtensionAPI } from "@earendil-w) (+15 more)

### Community 20 - "community-20"
Cohesion: 0.08
Nodes (24): Authenticate, code:bash (npm install -g @earendil-works/pi-coding-agent), code:bash (pi -p "Summarize this codebase"), code:bash (cd /path/to/project), code:text (/login), code:bash (export ANTHROPIC_API_KEY=sk-ant-...), code:text (Summarize this repository and tell me how to run its checks.), code:markdown (# Project Instructions) (+16 more)

### Community 21 - "community-21"
Cohesion: 0.09
Nodes (22): Clipboard not working, Clipboard Support, code:bash (# Update packages), code:bash (pkg install termux-api), code:bash (termux-setup-storage), code:bash (npm cache clean --force), code:`markdown (# Agent Environment: Termux on Android), code:block3 (+14 more)

### Community 22 - "community-22"
Cohesion: 0.09
Nodes (22): abort, code:json ({"type": "follow_up", "message": "Also check this image", "i), code:json ({"type": "response", "command": "follow_up", "success": true), code:json ({"type": "abort"}), code:json ({"type": "response", "command": "abort", "success": true}), code:json ({"type": "new_session"}), code:json ({"type": "new_session", "parentSession": "/path/to/parent-se), code:json ({"type": "response", "command": "new_session", "success": tr) (+14 more)

### Community 23 - "community-23"
Cohesion: 0.1
Nodes (20): All Actions, Application, code:json ({), code:json ({), code:json ({), Custom Configuration, Display and Message Queue, Emacs Example (+12 more)

### Community 24 - "community-24"
Cohesion: 0.11
Nodes (17): code:typescript (ctx.sessionManager.getEntries()       // All entries), code:typescript (pi.on("tool_result", async (event, ctx) => {), code:typescript (pi.on("tool_call", (event, ctx) => {), code:typescript (const usage = ctx.getContextUsage();), code:typescript (ctx.compact({), code:typescript (pi.on("before_agent_start", (event, ctx) => {), ctx.compact(), ctx.cwd (+9 more)

### Community 25 - "community-25"
Cohesion: 0.12
Nodes (17): after_provider_response, Agent Events, agent_start / agent_end, before_agent_start, before_provider_request, code:typescript (pi.on("before_agent_start", async (event, ctx) => {), code:typescript (pi.on("agent_start", async (_event, ctx) => {});), code:typescript (pi.on("turn_start", async (event, ctx) => {) (+9 more)

### Community 26 - "community-26"
Cohesion: 0.12
Nodes (17): BranchSummaryEntry, code:json ({"type":"model_change","id":"d4e5f6g7","parentId":"c3d4e5f6"), code:json ({"type":"thinking_level_change","id":"e5f6g7h8","parentId":"), code:json ({"type":"compaction","id":"f6g7h8i9","parentId":"e5f6g7h8","), code:json ({"type":"branch_summary","id":"g7h8i9j0","parentId":"a1b2c3d), code:json ({"type":"custom","id":"h8i9j0k1","parentId":"g7h8i9j0","time), code:json ({"type":"label","id":"j0k1l2m3","parentId":"i9j0k1l2","times), code:json ({"type":"session_info","id":"k1l2m3n4","parentId":"j0k1l2m3") (+9 more)

### Community 27 - "community-27"
Cohesion: 0.12
Nodes (17): code:typescript (import type { ExtensionAPI } from "@earendil-works/pi-coding), code:typescript (import { BorderedLoader } from "@earendil-works/pi-coding-ag), code:typescript (import { getSettingsListTheme } from "@earendil-works/pi-cod), code:typescript (// Set status (shown in footer)), code:typescript (// Static indicator), code:typescript (// Simple string array (above editor by default)), code:typescript (ctx.ui.setFooter((tui, theme, footerData) => ({), code:typescript (import { CustomEditor, type ExtensionAPI } from "@earendil-w) (+9 more)

### Community 28 - "community-28"
Cohesion: 0.12
Nodes (15): /../../../agents, /development, code:bash (git clone https://github.com/earendil-works/pi-mono), code:bash (/path/to/pi-mono/pi-test.sh), code:json ({), code:typescript (import { getPackageDir, getThemeDir } from "./config.js";), code:bash (./test.sh                         # Run non-LLM tests (no AP), code:block6 (packages/) (+7 more)

### Community 29 - "community-29"
Cohesion: 0.12
Nodes (16): code:typescript (interface Component {), code:typescript (import { matchesKey, Key } from "@earendil-works/pi-tui";), code:typescript (import { visibleWidth, truncateToWidth } from "@earendil-wor), code:typescript (import {), code:typescript (pi.registerCommand("pick", {), code:bash (PI_TUI_WRITE_LOG=/tmp/tui-ansi.log npx tsx packages/tui/test), code:typescript (class CachedComponent {), Component Interface (+8 more)

### Community 30 - "community-30"
Cohesion: 0.13
Nodes (14): code:block1 (keybind = alt+backspace=text:\x1b\x7f), code:block2 (keybind = shift+enter=text:\n), code:json ({), code:lua (local wezterm = require 'wezterm'), code:json ({), code:json ({), Ghostty, IntelliJ IDEA (Integrated Terminal) (+6 more)

### Community 31 - "community-31"
Cohesion: 0.14
Nodes (13): /prompt-templates, Argument Hints, Arguments, code:markdown (---), code:markdown (---), code:block3 (→ pr   <PR-URL>       — Review PRs from URLs with structured), code:block4 (/review                           # Expands review.md), code:markdown (---) (+5 more)

### Community 32 - "community-32"
Cohesion: 0.14
Nodes (13): code:block1 (~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl), code:block18 ([user msg] ─── [assistant] ─── [user msg] ─── [assistant] ─┬), code:typescript (import { readFileSync } from "fs";), code:typescript (interface SessionEntryBase {), Context Building, Deleting Sessions, Entry Base, File Location (+5 more)

### Community 33 - "community-33"
Cohesion: 0.14
Nodes (14): Branch Summaries, Branching with `/tree`, code:bash (pi -c                  # Continue most recent session), code:text (/name Refactor auth module), code:text (├─ user: "Hello, can you help..."), Naming Sessions, Resuming and Deleting Sessions, Selection Behavior (+6 more)

### Community 34 - "community-34"
Cohesion: 0.14
Nodes (10): Box, Built-in Components, code:typescript (const container = new Container();), code:typescript (const spacer = new Spacer(2);  // 2 empty lines), code:typescript (import { Text, Box, Container, Spacer, Markdown } from "@ear), Container, Image, Markdown (+2 more)

### Community 35 - "community-35"
Cohesion: 0.14
Nodes (13): /../examples/extensions/custom-footer.ts, /../examples/extensions/handoff.ts, /../examples/extensions/modal-editor.ts, /../examples/extensions/overlay-qa-tests.ts, /../examples/extensions/plan-mode.ts, /../examples/extensions/preset.ts, /../examples/extensions/qna.ts, /../examples/extensions/snake.ts (+5 more)

### Community 36 - "community-36"
Cohesion: 0.15
Nodes (13): code:typescript (pi.on("session_start", async (event, ctx) => {), code:typescript (pi.on("session_before_switch", async (event, ctx) => {), code:typescript (pi.on("session_before_fork", async (event, ctx) => {), code:typescript (pi.on("session_before_compact", async (event, ctx) => {), code:typescript (pi.on("session_before_tree", async (event, ctx) => {), code:typescript (pi.on("session_shutdown", async (event, ctx) => {), session_before_compact / session_compact, session_before_fork (+5 more)

### Community 37 - "community-37"
Cohesion: 0.17
Nodes (12): code:block10 (pi starts), code:typescript (pi.on("resources_discover", async (event, _ctx) => {), code:typescript (import { createLocalBashOperations } from "@earendil-works/p), code:typescript (pi.on("input", async (event, ctx) => {), Events, input, Input Events, Lifecycle Overview (+4 more)

### Community 38 - "community-38"
Cohesion: 0.17
Nodes (11): code:bash (pi --mode json "Your prompt"), code:typescript (type AgentSessionEvent =), code:typescript (type AgentEvent =), code:json ({"type":"session","version":3,"id":"uuid","timestamp":"...",), code:json ({"type":"agent_start"}), code:bash (pi --mode json "List files" 2>/dev/null | jq -c 'select(.typ), Event Types, Example (+3 more)

### Community 39 - "community-39"
Cohesion: 0.18
Nodes (11): code:bash (curl -fsSL https://pi.dev/install.sh | sh), code:bash (npm install -g @earendil-works/pi-coding-agent), code:bash (pi), Customization, Development, Pi Documentation, Platform setup, Programmatic usage (+3 more)

### Community 40 - "community-40"
Cohesion: 0.2
Nodes (10): abort_bash, Bash, bash, code:json ({"type": "bash", "command": "ls -la"}), code:json ({), code:json ({), code:` (Ran `ls -la`), code:block49 (+2 more)

### Community 41 - "community-41"
Cohesion: 0.2
Nodes (10): code:json ({"type": "set_model", "provider": "anthropic", "modelId": "c), code:json ({), code:json ({"type": "cycle_model"}), code:json ({), code:json ({"type": "get_available_models"}), code:json ({), cycle_model, get_available_models (+2 more)

### Community 42 - "community-42"
Cohesion: 0.22
Nodes (9): AgentMessage Union, Base Message Types (from pi-ai), code:typescript (interface TextContent {), code:typescript (interface UserMessage {), code:typescript (interface BashExecutionMessage {), code:typescript (type AgentMessage =), Content Blocks, Extended Message Types (from pi-coding-agent) (+1 more)

### Community 43 - "community-43"
Cohesion: 0.22
Nodes (8): code:tmux (set -g extended-keys on), code:bash (tmux kill-server), code:tmux (set -g extended-keys on), Recommended Configuration, Requirements, tmux Setup, What This Fixes, Why `csi-u` Is Recommended

### Community 44 - "community-44"
Cohesion: 0.25
Nodes (8): code:typescript (import { isToolCallEventType } from "@earendil-works/pi-codi), code:typescript (// my-extension.ts), code:typescript (import { isToolCallEventType } from "@earendil-works/pi-codi), code:typescript (import { isBashToolResult } from "@earendil-works/pi-coding-), tool_call, Tool Events, tool_result, Typing custom tool input

### Community 45 - "community-45"
Cohesion: 0.25
Nodes (8): code:json ({"type": "compact"}), code:json ({"type": "compact", "customInstructions": "Focus on code cha), code:json ({), code:json ({"type": "set_auto_compaction", "enabled": true}), code:json ({"type": "response", "command": "set_auto_compaction", "succ), compact, Compaction, set_auto_compaction

### Community 46 - "community-46"
Cohesion: 0.25
Nodes (8): code:typescript (class BadComponent extends Container {), code:typescript (class GoodComponent extends Container {), code:typescript (class ComplexComponent extends Container {), Invalidation and Theme Changes, Pattern: Rebuild on Invalidate, The Problem, The Solution, When This Matters

### Community 47 - "community-47"
Cohesion: 0.29
Nodes (7): abort_retry, code:json ({"type": "set_auto_retry", "enabled": true}), code:json ({"type": "response", "command": "set_auto_retry", "success":), code:json ({"type": "abort_retry"}), code:json ({"type": "response", "command": "abort_retry", "success": tr), Retry, set_auto_retry

### Community 48 - "community-48"
Cohesion: 0.29
Nodes (7): code:json ({"type": "get_state"}), code:json ({), code:json ({"type": "get_messages"}), code:json ({), get_messages, get_state, State

### Community 49 - "community-49"
Cohesion: 0.29
Nodes (7): code:json ({"type": "set_thinking_level", "level": "high"}), code:json ({"type": "response", "command": "set_thinking_level", "succe), code:json ({"type": "cycle_thinking_level"}), code:json ({), cycle_thinking_level, set_thinking_level, Thinking

### Community 50 - "community-50"
Cohesion: 0.29
Nodes (7): code:json ({"type": "set_steering_mode", "mode": "one-at-a-time"}), code:json ({"type": "response", "command": "set_steering_mode", "succes), code:json ({"type": "set_follow_up_mode", "mode": "one-at-a-time"}), code:json ({"type": "response", "command": "set_follow_up_mode", "succe), Queue Modes, set_follow_up_mode, set_steering_mode

### Community 51 - "community-51"
Cohesion: 0.29
Nodes (7): Instance Methods - Appending (all return entry ID), Instance Methods - Context & Info, Instance Methods - Session Management, Instance Methods - Tree Navigation, SessionManager API, Static Creation Methods, Static Listing Methods

### Community 52 - "community-52"
Cohesion: 0.4
Nodes (5): code:typescript (pi.on("model_select", async (event, ctx) => {), code:typescript (pi.on("thinking_level_select", async (event, ctx) => {), Model Events, model_select, thinking_level_select

### Community 53 - "community-53"
Cohesion: 0.4
Nodes (5): code:json ({"type": "get_commands"}), code:json ({), Commands, Commands, get_commands

### Community 54 - "community-54"
Cohesion: 0.4
Nodes (3): code:typescript (// Wrong - stale reference), Overlay Lifecycle, Overlays

### Community 55 - "community-55"
Cohesion: 0.5
Nodes (4): code:typescript (import { CURSOR_MARKER, type Component, type Focusable } fro), code:typescript (import { Container, type Focusable, Input } from "@earendil-), Container Components with Embedded Inputs, Focusable Interface (IME Support)

### Community 56 - "community-56"
Cohesion: 0.5
Nodes (4): code:typescript (renderResult(result, options, theme, context) {), code:typescript (import { getMarkdownTheme } from "@earendil-works/pi-coding-), code:typescript (interface MyTheme {), Theming

### Community 57 - "community-57"
Cohesion: 0.67
Nodes (3): code:json ({"type":"session","version":3,"id":"uuid","timestamp":"2024-), code:json ({"type":"session","version":3,"id":"uuid","timestamp":"2024-), SessionHeader

### Community 58 - "community-58"
Cohesion: 0.67
Nodes (3): code:typescript (pi.on("session_start", async (_event, ctx) => {), code:typescript (async execute(toolCallId, params, onUpdate, ctx, signal) {), Using Components

## Knowledge Gaps
- **627 isolated node(s):** `Overview`, `code:block1 (contextTokens > contextWindow - reserveTokens)`, `code:block2 (Before compaction:)`, `code:block3 (Split turn (one huge turn exceeds budget):)`, `Cut Point Rules` (+622 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Extensions` connect `community-3` to `community-2`, `community-37`, `community-17`, `community-19`, `community-24`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Why does `Events` connect `community-37` to `community-25`, `community-36`, `community-52`, `community-44`?**
  _High betweenness centrality (0.000) - this node is a cross-community bridge._
- **What connects `Overview`, `code:block1 (contextTokens > contextWindow - reserveTokens)`, `code:block2 (Before compaction:)` to the rest of the system?**
  _627 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `community-0` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `community-1` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `community-2` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `community-3` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `community-4` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `community-5` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `community-6` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._