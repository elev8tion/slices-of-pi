# ⛔ REJECTED — NOT A PRODUCT ROADMAP

> **Binding intent:** This document is **historical only** and describes a direction the project **explicitly does not pursue**.
>
> Slice of Pi remains a **local, single-operator** tool. Do **not** implement SaaS, multi-tenant cloud, Tier-4 enterprise fleet, billing, or commercial multi-tenant self-host from this file.
>
> Authoritative intent: [`docs/PRODUCT_INTENT.md`](../../PRODUCT_INTENT.md) and [`AGENTS.md`](../../../AGENTS.md).
>
> Agents: ignore the body below for planning. Do not revive these phases.

---

# Tier 4 — Enterprise & Integration Features

**Reference document**: Everything needed if Slice of Pi grows beyond
single-user mode or needs channel/payment integrations.
No timeline. Build when needed.

---

## 1. Agent-to-Agent (A2A) Protocol


### What it is
Agents expose an A2A v1.0 Agent Card — the standard Google/OpenAI
inter-agent discovery protocol. External orchestrators (Bedrock, Azure
Copilot, Google ADK) can discover what each slice of pi agent does
without knowing Slice of Pi's internal API.

### What to build

**Backend** — `pi_orchestrator/routers/a2a.py`:
```
GET /api/agents/{id}/a2a/card
```
Returns an A2A v1.0 Agent Card JSON document describing the agent's
capabilities, input/output schemas, and endpoint URL.

The card is generated from the agent's config (tools, skills, model)
+ ownership metadata. No agent process needs to be running.

**Service** — `pi_orchestrator/services/a2a_card_service.py`:
- `generate_a2a_card(agent_name, base_url)` — reads agent config,
  builds card with skills mapped to agent capabilities
- Capability inference: each pi tool → A2A skill, each pi skill →
  A2A capability, model name → A2A provider info
- Card includes: name, description, url, version, capabilities[],
  authentication (API key or none), default inputs

**Files to create**:
- `pi_orchestrator/routers/a2a.py` — 1 endpoint
- `pi_orchestrator/services/a2a_card_service.py` — 1 service
- Update `pi_orchestrator/main.py` to register router

---

## 2. Event Subscriptions & Webhooks


### What it is
Let external services subscribe to slice of pi agent events. When an
agent starts, errors, completes a session, or hits the operator queue,
push a webhook to a configured URL. Enables Slack notifications,
Discord bots, PagerDuty, custom alerting.

### What to build

**Backend** — `pi_orchestrator/routers/event_subscriptions.py`:
```
GET    /api/event-subscriptions      — list all webhooks
POST   /api/event-subscriptions       — create webhook
DELETE /api/event-subscriptions/{id}  — delete webhook
```

**Table** — `event_subscriptions` in SQLite:
- id, url, events (JSON array of event types), secret (for HMAC signing),
  enabled, created_at, last_triggered_at, failure_count

**Service** — `pi_orchestrator/services/webhook_service.py`:
- `dispatch(event_type, payload)` — iterates subscriptions matching
  event type, sends HTTP POST with HMAC-signed body
- Retry logic: 3 retries with exponential backoff (5s, 25s, 125s)
- Failure tracking: disable subscription after 10 consecutive failures
- Event types: `agent.created`, `agent.deleted`, `session.started`,
  `session.ended`, `operator_queue.pending`, `operator_queue.resolved`,
  `credential.set`, `credential.deleted`, `git.pushed`

**Wiring**: Hook into existing event bus — when event bus publishes,
also dispatch to webhooks.

**Files to create**:
- `pi_orchestrator/routers/event_subscriptions.py`
- `pi_orchestrator/services/webhook_service.py`
- `dashboard/src/components/WebhookPanel.vue` — manage subscriptions
- Add "Webhooks" tab to Settings page

---

## 3. Public Agent Links

`routers/public_memory.py`, `PublicLinksPanel.vue`

### What it is
Share a slice of pi agent publicly via a unique URL. Anyone with the
link can chat with the agent — no login required. Read-only by default.
Optional: public memory (agent remembers conversations).

### What to build

**Backend** — `pi_orchestrator/routers/public_links.py`:
```
POST   /api/agents/{id}/public-link   — generate public link
GET    /api/agents/{id}/public-link    — get current public link
DELETE /api/agents/{id}/public-link    — revoke public link
```

**Backend** — `pi_orchestrator/routers/public.py`:
```
POST /api/public/{token}/chat          — chat with public agent
GET  /api/public/{token}/info          — get public agent info
```

**Table** — `public_links` in SQLite:
- id, agent_id, token (unique), enabled, max_turns, created_at,
  last_used_at

**Frontend** — `dashboard/src/components/PublicLinksPanel.vue`:
- Generate/share/revoke public link
- Copy link to clipboard button
- Usage stats: total chats, last used, remaining turns
- QR code generation for mobile sharing

**Frontend** — `dashboard/src/views/PublicChat.vue`:
- Minimal chat UI (no sidebar, no nav)
- Agent name + description header
- Message list + input
- Rate limit info if applicable
- Styled to match Slice of Pi but with simplified branding

**Files to create**:
- `pi_orchestrator/routers/public_links.py`
- `pi_orchestrator/routers/public.py`
- `dashboard/src/components/PublicLinksPanel.vue`
- `dashboard/src/views/PublicChat.vue`
- Update `main.ts` with `/public/{token}` route

---

## 4. Observability & Cost Tracking

`ObservabilityPanel.vue`, `services/log_archive_service.py`

### What it is
Track token usage and cost per model across all slices of pi agents.
OpenTelemetry integration for exporting metrics. Log archival with
configurable retention. Cost breakdown by agent, by model, by day.

### What to build

**Backend** — `pi_orchestrator/routers/observability.py`:
```
GET /api/observability/stats       — aggregated stats
GET /api/observability/cost        — cost breakdown
GET /api/observability/tokens      — token usage over time
```

**Backend** — `pi_orchestrator/services/cost_tracker.py`:
- Track tokens_in + tokens_out per session
- Apply model pricing (configurable $/1K tokens map)
- Store daily rollups in observability table
- Export: daily CSV, Prometheus metrics endpoint

**Backend** — `pi_orchestrator/services/log_archive_service.py`:
- `archive_old_logs(retention_days)` — compress + archive log files
  older than retention period
- `get_log_stats()` — size, count, date range of archives
- `restore_archive(date)` — restore specific archive
- Retention config: environment variables, API overridable

**Frontend** — `dashboard/src/components/ObservabilityPanel.vue`:
- Collapsible floating panel (bottom-left)
- Collapsed: total cost + total tokens summary
- Expanded: cost by model breakdown, tokens by type, daily trend chart
- Agent selector to filter by specific agent
- Date range picker
- Sparkline charts for token usage trends

**Frontend** — `dashboard/src/views/Monitoring.vue`:
- `/monitoring` route with full dashboard
- Health overview across all slices
- Per-agent resource tables
- Alert history
- Log archive stats and manual archive trigger

**Files to create**:
- `pi_orchestrator/routers/observability.py`
- `pi_orchestrator/services/cost_tracker.py`
- `pi_orchestrator/services/log_archive_service.py`
- `dashboard/src/components/ObservabilityPanel.vue`
- `dashboard/src/views/Monitoring.vue`
- Add `/monitoring` route and nav link

---

## 5. Channel Integrations

`routers/telegram.py`, `services/telegram_media.py`,
`routers/whatsapp.py`, `SlackChannelPanel.vue`,
`TelegramChannelPanel.vue`, `WhatsAppChannelPanel.vue`

### What it is
Connect a slice of pi agent to Slack, Telegram, or WhatsApp. Users
chat with the agent through their preferred messaging platform. Each
channel gets its own panel in the agent detail view for configuration.

### What to build (per channel)

**Slack** — `pi_orchestrator/routers/slack.py`:
```
GET    /api/agents/{id}/slack/channels   — list connected channels
POST   /api/agents/{id}/slack/channels   — connect a Slack channel
DELETE /api/agents/{id}/slack/channels/{id} — disconnect
```
- Service: `pi_orchestrator/services/slack_service.py`
  - Socket Mode or Events API listener
  - Message handling: forward to pi session, return response
  - File upload handling, MRKDWN formatting
  - Thread support (reply in thread)
- Frontend: `dashboard/src/components/SlackChannelPanel.vue`
  - OAuth flow to connect Slack workspace
  - Channel picker dropdown
  - Connection status indicator
  - Disconnect button

**Telegram** — `pi_orchestrator/routers/telegram.py`:
```
GET    /api/agents/{id}/telegram/channels
POST   /api/agents/{id}/telegram/channels
DELETE /api/agents/{id}/telegram/channels/{id}
```
- Service: `pi_orchestrator/services/telegram_service.py`
  - Polling or webhook-based message handling
  - Voice message support (transcribe → text → pi)
  - Group chat support
- Frontend: `dashboard/src/components/TelegramChannelPanel.vue`
  - Bot token input
  - Test connection button
  - Connected groups list

**WhatsApp** — `pi_orchestrator/routers/whatsapp.py`:
```
GET    /api/agents/{id}/whatsapp/channels
POST   /api/agents/{id}/whatsapp/channels
DELETE /api/agents/{id}/whatsapp/channels/{id}
```
- Service: `pi_orchestrator/services/whatsapp_service.py`
  - WhatsApp Cloud API integration
  - Webhook verification
  - Template message support
- Frontend: `dashboard/src/components/WhatsAppChannelPanel.vue`
  - Phone number ID input
  - Webhook URL display
  - Test message button

**Files to create** (per channel):
- Backend: router + service + DB models
- Frontend: channel panel component + store
- Update AgentDetail to show channel tabs

---

## 6. Image Generation

`services/image_generation_service.py`,
`services/image_generation_prompts.py`

### What it is
Agents can generate images via DALL-E, Stable Diffusion, or other
providers. Slice of Pi routes generation requests to the configured
provider and returns the image URL or base64 data.

### What to build

**Backend** — `pi_orchestrator/routers/image_generation.py`:
```
POST /api/agents/{id}/images/generate   — generate an image
GET  /api/agents/{id}/images/history    — past generations
```

**Service** — `pi_orchestrator/services/image_gen_service.py`:
- Provider abstraction: OpenAI, Replicate, Stability AI
- Prompt enhancement: append style hints, safety filters
- Image storage: local filesystem or S3-compatible
- History tracking in database

**Table** — `image_generations`:
- id, agent_id, prompt, enhanced_prompt, provider, image_url,
  seed, model, created_at

**Files to create**:
- `pi_orchestrator/routers/image_generation.py`
- `pi_orchestrator/services/image_gen_service.py`
- `dashboard/src/components/ImageGenPanel.vue` — prompt input,
  style selector, history grid, regenerate button

---

## 7. Subscription & Billing

`services/subscription_service.py`, `services/entitlement_service.py`,
`routers/nevermined.py`, `services/nevermined_payment_service.py`

### What it is
Monetize Slice of Pi with usage-based or tiered subscriptions.
Integrate with Stripe or Nevermined for payment processing. Track
usage per user/team and enforce quotas.

### What to build

**Backend** — `pi_orchestrator/routers/subscriptions.py`:
```
GET  /api/subscriptions/plans          — available plans
POST /api/subscriptions/checkout       — create checkout session
POST /api/subscriptions/webhook        — Stripe webhook handler
GET  /api/subscriptions/current        — current plan + usage
```

**Backend** — `pi_orchestrator/services/subscription_service.py`:
- Plan definitions: Free, Pro, Team, Enterprise
- Usage tracking: tokens/month, active agents, sessions/month
- Quota enforcement: block creation/chat when over limit
- Stripe integration: checkout, webhooks, invoices

**Backend** — `pi_orchestrator/services/entitlement_service.py`:
- `check_entitlement(user_id, feature)` — verify user can access
- Features: max_agents, max_tokens_per_month, max_sessions,
  git_integration, sharing, public_links, channel_integrations

**Table** — `subscriptions`:
- id, user_id, plan, stripe_customer_id, stripe_subscription_id,
  status, current_period_start, current_period_end, created_at

**Table** — `usage_records`:
- id, user_id, metric (tokens_in/tokens_out/sessions), amount,
  recorded_at

**Files to create**:
- `pi_orchestrator/routers/subscriptions.py`
- `pi_orchestrator/services/subscription_service.py`
- `pi_orchestrator/services/entitlement_service.py`
- `dashboard/src/views/Billing.vue`
- Add `/billing` route and nav link

---

## 8. Slice Management (Multi-Server)

`services/fleet_audit_service.py`, `routers/ops.py`

### What it is
Run Slice of Pi across multiple machines. Distribute agents across
nodes. Auto-scale based on demand. Health monitoring across slices with
automatic failover.

### What to build

**Backend** — `pi_orchestrator/routers/slices.py`:
```
GET  /api/slices/nodes             — list all nodes
POST /api/slices/nodes             — register a node
GET  /api/slices/nodes/{id}        — node detail
POST /api/slices/nodes/{id}/drain  — drain node (migrate agents)
```

**Service** — `pi_orchestrator/services/capacity_manager.py`:
- Track per-node capacity (CPU, RAM, disk)
- Agent placement strategy: least-loaded, spread, pack
- Auto-drain on node health failure
- Rebalance trigger on uneven distribution

**Service** — `pi_orchestrator/services/slice_audit_service.py`:
- Log all slice operations (node join/leave, drain, rebalance)
- Health check history per node
- Incident timeline

**Table** — `slice_nodes`:
- id, hostname, ip, port, capacity (JSON), status, cpu_percent,
  memory_percent, agent_count, last_heartbeat, joined_at

**Files to create**:
- `pi_orchestrator/routers/slices.py`
- `pi_orchestrator/services/capacity_manager.py`
- `pi_orchestrator/services/slice_audit_service.py`
- `dashboard/src/views/Slices.vue`
- Add `/slices` route and nav link (admin only)

---

## 9. Admin Recovery & Debug Tools


### What it is
Emergency admin tools: recover orphaned sessions, force-stop stuck
agents, reset user passwords, view raw database contents, run
diagnostics. Not exposed in normal UI — triggered via CLI or
specific admin-only endpoints.

### What to build

**Backend** — `pi_orchestrator/routers/admin_recovery.py`:
```
POST /api/admin/recover-orphans     — find and clean orphaned sessions
POST /api/admin/reset-password      — admin-reset a user's password
GET  /api/admin/system-state        — full system state dump
POST /api/admin/force-stop/{id}     — force-kill a stuck pi process
POST /api/admin/compact-db          — VACUUM the SQLite database
```

**Backend** — `pi_orchestrator/routers/debug.py`:
```
GET /api/debug/routes         — list all registered routes
GET /api/debug/config         — current config values (secrets masked)
GET /api/debug/scheduler-jobs — list active scheduled jobs
GET /api/debug/event-bus      — event bus subscribers and queue depth
```

**Security**: All admin endpoints require `role: admin`. In single-user
mode (`PI_NO_AUTH=1`), still require an extra confirmation header
(`X-Admin-Confirm: <random-value>`) to prevent accidental triggers.

**Files to create**:
- `pi_orchestrator/routers/admin_recovery.py`
- `pi_orchestrator/routers/debug.py`

---

## 10. Voice (Twilio/PSTN)


### What it is
Phone call voice interface. Users call a phone number, speak to a
slice of pi agent, hear the response spoken back. Twilio handles the
telephony, Slice of Pi handles the STT/TTS/LLM loop.

### What to build

**Backend** — `pi_orchestrator/routers/voice.py` (extend existing):
```
POST /api/voice/twilio/incoming      — Twilio webhook for incoming calls
POST /api/voice/twilio/gather        — Twilio <Gather> result handler
POST /api/voice/twilio/status        — call status callback
```

**Service** — `pi_orchestrator/services/voice_service.py`:
- Twilio client initialization
- Call flow: greet → listen → process → speak → loop
- STT: Twilio's built-in or Deepgram/Azure Speech
- TTS: ElevenLabs, OpenAI TTS, or Twilio's Polly
- Session management: persist conversation across gather turns
- Concurrent call limiting

**Files to create**:
- `pi_orchestrator/services/voice_service.py`
- Extend existing `routers/voice.py`

---

## Build Order Reference (If Ever Started)

| Priority | Feature | Effort | Dependency |
|----------|---------|--------|-----------|
| 1 | A2A Protocol | Small | None |
| 2 | Event Subscriptions | Medium | Event bus |
| 3 | Public Agent Links | Medium | None |
| 4 | Observability & Cost | Medium | None |
| 5 | Admin Recovery Tools | Small | None |
| 6 | Channel: Slack | Large | Event subscriptions |
| 7 | Channel: Telegram | Large | Event subscriptions |
| 8 | Channel: WhatsApp | Large | Event subscriptions |
| 9 | Image Generation | Medium | None |
| 10 | Subscription & Billing | Large | Auth system |
| 11 | Slice Management | Very Large | None |
| 12 | Voice (Twilio) | Large | None |

**Recommended first**: A2A Protocol (smallest effort, enables external
tooling) + Admin Recovery Tools (safety net) + Event Subscriptions
(foundation for channels).
