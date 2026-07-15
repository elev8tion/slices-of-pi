# Productizing Slice of Pi

**Current state**: Single-user mode (`PI_NO_AUTH=1`). No login required.
Everything runs on your Mac, bound to localhost.

This document maps the path from here to three future states:

1. **Share with a team** (self-hosted, multi-user)
2. **Open source release** (public on GitHub, community contributions)
3. **Commercial product** (SaaS or paid self-hosted)

---

## Phase 0 — Current State (Development)

```
Architecture:
  Browser → localhost:8420 → FastAPI → pi binary
                              ├── SQLite (~/.pi/agent/orchestrator.db)
                              └── JSONL sessions (~/.pi/agent/sessions/)
```

**Already works today:**
- All 13 features across 4 phases
- Chat, terminal, voice, git, credentials, audit log, operator queue
- WebSocket ticket auth (currently bypassed by PI_NO_AUTH)
- WebSocket event bus

**Baked-in single-user assumptions:**
- `PI_NO_AUTH=1` env var bypasses all auth
- SQLite file at `~/.pi/agent/` — no connection pooling needed
- Everything on localhost, no HTTPS, no CORS concerns
- pi binary on the same machine
- No rate limiting, no user isolation

---

## Phase 1 — Share with a Team (self-hosted)

### What changes

**Enable real auth:**
- Remove `PI_NO_AUTH=1` from the `./slices` script
- Users register their own accounts via the /login page
- JWT tokens protect all API endpoints
- Admin user manages other users

**Switch to a real database:**
| Current | For a team |
|---------|-----------|
| SQLite (`orchestrator.db`) | PostgreSQL |
| Thread-local connections | Connection pool (asyncpg/psycopg3) |
| No migrations | Alembic or similar migration tool |

**Move to a proper server:**
| Current | For a team |
|---------|-----------|
| localhost:8420 | Your server IP or domain |
| No HTTPS | Let's Encrypt + nginx reverse proxy |
| Built-in dashboard serving | Nginx serves static files, proxies API |

**Add team sharing:**
- The `sharing` router already exists (`POST /api/agents/{id}/shares`)
- Works via email → user lookup → permission assignment
- Access requests queue already built
- Just needs the `PI_NO_AUTH=1` guard removed

**What already exists and just works:**
- ✅ User registration and login (`/api/auth/register`, `/api/auth/login`)
- ✅ JWT token system (24h expiry, HMAC-SHA256)
- ✅ Agent sharing by email with chat/admin permissions
- ✅ Access requests with approve/reject
- ✅ User management (`/api/users`, `/api/users/search`)
- ✅ Audit log (tracks who did what)

**What needs to be built for teams:**
| Feature | Why |
|---------|-----|
| Password reset flow | Users forget passwords |
| Email verification | Prevent bot registrations |
| Rate limiting | Prevent brute force on login |
| Session isolation | Agent A's data not visible to User B |
| Admin dashboard | Manage users, reset passwords, view logs |

**Estimated effort**: 1-2 weeks

---

## Phase 2 — Open Source Release

### What changes beyond Phase 1

**Clean the codebase:**
```markdown
- [ ] Remove any hardcoded paths (~/.pi/agent → configurable via env)
- [ ] Add a proper `config.yaml` file with all settings
- [ ] Add proper error handling for all edge cases
- [ ] Add a `--help` CLI with all flags documented
- [ ] Add CONTRIBUTING.md, CODE_OF_CONDUCT.md, LICENSE
- [ ] Add issue templates for GitHub
```

**Add Docker support:**
```
docker-compose.yml:
  - slice-of-pi-api (the FastAPI server)
  - slice-of-pi-db (PostgreSQL)
  - slice-of-pi-dashboard (nginx serving built Vue app)
  - redis? (for WebSocket pub/sub across multiple API instances)
```

**Add comprehensive tests:**
- Unit tests for every backend endpoint (pytest, ~200 tests)
- Frontend component tests (Vitest, ~50 tests)
- E2E tests with Playwright (critical user flows)
- Load testing (locust or k6)

**Add documentation:**
- Quickstart guide (5-minute setup)
- Configuration reference
- API reference (auto-generated from OpenAPI)
- Architecture overview
- Deployment guide (bare metal, Docker, Kubernetes)

**Package for distribution:**
- PyPI package for the backend (`pip install slice-of-pi`)
- NPM package for the dashboard widgets (optional)
- Homebrew formula for macOS
- Docker image on Docker Hub / GitHub Container Registry

**What we already have for open source:**
- ✅ `.gitignore`
- ✅ `pyproject.toml` with dependencies
- ✅ MIT-style or unrestrictive code patterns
- ✅ `README.md` with project description

**Estimated effort**: 2-4 weeks (plus ongoing maintenance)

---

## Phase 3 — Commercial Product (SaaS or Paid)

### Option A: SaaS (you host it)

**Infrastructure:**
| Component | What you need |
|-----------|---------------|
| App servers | 2+ instances behind a load balancer |
| Database | Managed PostgreSQL (RDS, Cloud SQL, etc.) |
| File storage | S3/R2 for agent session files + logs |
| WebSocket pub/sub | Redis or PostgreSQL LISTEN/NOTIFY |
| Domain + SSL | Cloudflare + Let's Encrypt |
| Monitoring | Datadog, Grafana, or Sentry |
| CI/CD | GitHub Actions → deploy to your cloud |

**Multi-tenancy:**
- Every user/team gets an isolated "slice" namespace
- Database: `agent_<tenant_id>` prefix or separate schema per tenant
- Sessions: tenant-isolated storage paths
- Rate limits per tenant
- Usage tracking per tenant (for billing)

**Billing integration:**
```python
# Already conceptualized in FUTURE_TIER4.md:
POST /api/subscriptions/checkout  → Stripe checkout session
POST /api/subscriptions/webhook   → Stripe event handler
GET  /api/subscriptions/current   → current plan + usage
```

**Pricing tiers (example):**
| Tier | Price | Limits |
|------|-------|--------|
| Free | $0 | 1 agent, 100 sessions/month, 50K tokens/month |
| Pro | $20/mo | 5 agents, unlimited sessions, 1M tokens/month |
| Team | $100/mo | 25 agents, team sharing, audit log |
| Enterprise | Custom | Unlimited, SSO, dedicated support |

**What already exists:**
- ✅ User system with roles
- ✅ Agent sharing
- ✅ Operator queue (for human-in-loop approval)
- ✅ Monitoring endpoints
- ✅ Observability/cost tracking (planned in FUTURE_TIER4)

**What needs to be built:**
| Feature | Why |
|---------|-----|
| Stripe integration | Payment processing |
| Usage quotas | Enforce plan limits |
| Tenant isolation | Separate data between customers |
| Onboarding flow | Welcome emails, tutorials |
| Support system | In-app chat or email integration |
| Uptime monitoring | Keep the service running |
| Backup strategy | Regular DB + file backups |
| GDPR compliance | Data export, delete, privacy policy |

### Option B: Commercial self-hosted (they run it)

Same as Phase 1 (team self-hosted), plus:
- License key system (validate on boot against your server)
- Premium features gated behind license
- Priority support / SLAs
- Automated deployment scripts (Ansible, Terraform)

---

## Decision Tree

```
Are you building for yourself?
  └─ ✅ Current state (PI_NO_AUTH=1, localhost)
      You're done. Everything works.

Want to share with a few teammates?
  └─ Phase 1 (add real auth, PostgreSQL, team sharing)
      ~1-2 weeks of work.

Want to release as open source?
  └─ Phase 1 + Phase 2 (clean code, Docker, docs, tests, packaging)
      ~3-6 weeks total.

Want to sell as a product?
  └─ Phase 1 + Phase 2 + Phase 3
      ~8-16 weeks depending on scope.
```

## What You Own vs What You'd Need to Build

### Already Built (Phases 1-4)

```
Chat UI ─────────── ChatBubble, ChatMessages, ChatInput, HistoryDropdown
Productivity ────── SlicePlays, Info Panel, StatusIndicator, WS Ticket Auth
Observability ───── Audit Log, Slice Operations, MCP Keys
Polish ──────────── RuntimeBadge, CapacityMeter, ResourceModal, HelpPanel
System ──────────── Terminal, System Console, Host Telemetry, Notifications
Data ────────────── Tags, Credentials (encrypted), Git integration
Chat ────────────── SSE streaming, session resume/fork, file attach
Platform ────────── Agent CRUD, sessions, schedules, templates, teams
```

### Would Need to Build (from FUTURE_TIER4.md)

```
Enterprise ─────── A2A protocol, public agent links, event webhooks
Channels ───────── Slack, Telegram, WhatsApp integrations
Payments ───────── Stripe subscriptions, usage quotas, entitlements
Infrastructure ─── Multi-server fleet, PostgreSQL, Redis, Docker
Security ───────── SSO, SAML, audit hashing, penetration testing
```

---

## Quick Reference: Key Files That Would Change

| File | What it does in prod |
|------|---------------------|
| `pi_orchestrator/config.py` | Add `DATABASE_URL`, `REDIS_URL`, `STORAGE_BACKEND` |
| `pi_orchestrator/database.py` | Swap SQLite for async PostgreSQL driver |
| `pi_orchestrator/services/event_bus.py` | Swap in-process for Redis pub/sub |
| `pi_orchestrator/routers/auth.py` | Remove `PI_NO_AUTH` branch, add password reset |
| `dashboard/src/stores/auth.ts` | Remove `checkNoAuth()`, always require token |
| `slices` | Remove `PI_NO_AUTH=1`, add config loading |
| `start-orchestrator.py` | Add CLI flags for --db-url, --redis-url, --storage-dir |
