# E2E Probe
SHA: 9249dfa
date: 2026-07-15T05:49:27Z
pi: 0.80.7

## health
{"status":"ok","version":"0.1.0","agent_count":8,"active_session_count":1}
## docs status
200
## SPA root
200
## list agents
[{"id":"bhDVBBHFYMwF1HEhe078bA","name":"test-agent-share","persona":null,"status":"created","model":"","tokens_used":0,"session_count":0,"last_active":null,"created_at":"2026-06-14T08:18:46.217897Z"},{"id":"UuwG_kRQI0NLuJm89asj4g","name":"calculator","persona":null,"status":"idle","model":"","tokens_used":45376,"session_count":2,"last_active":"2026-06-12T18:11:13.745221Z","created_at":"2026-06-12T18:10:01.242335Z"},{"id":"Os9Gywu0_vWJKxUhQj5n7g","name":"b0b5acfeeb9ef53430be7eaac03cf964","persona":null,"status":"created","model":"that","tokens_used":0,"session_count":0,"last_active":null,"created_at":"2026-06-12T18:08:20.502637Z"},{"id":"t_R9tD91vn59YTDDWo9NHw","name":"ae075daf3729a0263183556d83c9b770","persona":null,"status":"created","model":"that","tokens_used":0,"session_count":0,"last_active":null,"created_at":"2026-06-12T18:08:01.033743Z"},{"id":"6-M4YdkMOuPaMqRKhw_9wg","name":"66f70b8cdf5c68958434ae76fdfca94d","persona":null,"status":"created","model":"that","tokens_used":0,"session_count":0,"last_active":null,"created_at":"2026-06-12T18:07:44.386699Z"},{"id":"QI5NkTxU6kiwBgiwHw-5FA","name":"expire-test-agent","persona":null,"status":"idle","model":"sonnet","tokens_used":0,"session_count":1,"last_active":"2026-06-12T18:06:52.543584Z","created_at":"2026-06-12T17:14:45.107585Z"},{"id":"Ools1sPDs6mGV-i9apHXkg","name":"f1cb4946354f67a602f16e8fe9946bbc","persona":null,"status":"created","model":"voice-test","tokens_used":0,"session_count":0,"last_active":null,"created_at":"2026-06-11T07:12:33.139789Z"},{"id":"BaB2nlRwZP5Bc9ouYmEloA","name":"demo-agent","persona":null,"status":"idle","model":"","tokens_used":0,"session_count":0,"last_active":"2026-06-11T06:40:51.162135Z","created_at":"2026-06-11T06:40:51.157991Z"}]
## create agent
{"id":"3U6NPv6xCngXuH5VNkLiTg","name":"health-probe-agent","persona":null,"status":"idle","model":"","tokens_used":0,"session_count":0,"last_active":"2026-07-15T05:49:28.749318Z","created_at":"2026-07-15T05:49:28.746890Z"}
agent_id=3U6NPv6xCngXuH5VNkLiTg
## get agent
{"id":"3U6NPv6xCngXuH5VNkLiTg","name":"health-probe-agent","persona":null,"status":"idle","model":"","tokens_used":0,"session_count":0,"last_active":"2026-07-15T05:49:28.749318Z","created_at":"2026-07-15T05:49:28.746890Z","tools":["read","bash","web_search"],"skills":[],"extensions":[],"system_prompt":null,"git_repo":null,"schedule":null}
## chat (real pi)
data: {"type": "text_start"}

data: {"type": "text_delta", "content": "pong"}

data: {"type": "text_end"}


## sessions
[{"id":"DV2UqdRHtfONNP2KdxJCyg","agent_id":"3U6NPv6xCngXuH5VNkLiTg","agent_name":"health-probe-agent","session_file":"/Users/kc/.pi/agent/sessions/managed/health-probe-agent/DV2UqdRHtfONNP2KdxJCyg.jsonl","status":"running","turns":0,"tokens_in":0,"tokens_out":0,"model":"","started_at":"2026-07-15T05:49:28.808750+00:00","ended_at":null},{"id":"3vko61-MVpwkbsDXS62c3g","agent_id":"UuwG_kRQI0NLuJm89asj4g","agent_name":"calculator","session_file":"/Users/kc/.pi/agent/sessions/managed/calculator/3vko61-MVpwkbsDXS62c3g.jsonl","status":"completed","turns":4,"tokens_in":0,"tokens_out":6977,"model":"","started_at":"2026-06-12T18:10:50.043643+00:00","ended_at":"2026-06-12T18:11:13.743956+00:00"},{"id":"oxPexYl0KBWtmOH8AdVMLQ","agent_id":"UuwG_kRQI0NLuJm89asj4g","agent_name":"calculator","session_file":"/Users/kc/.pi/agent/sessions/managed/calculator/oxPexYl0KBWtmOH8AdVMLQ.jsonl","status":"completed","turns":2,"tokens_in":0,"tokens_out":38399,"model":"","started_at":"2026-06-12T18:10:25.470091+00:00","ended_at":"2026-06-12T18:10:36.543300+00:00"},{"id":"B1sqGBZ0QWMxMyojbrLVYg","agent_id":"QI5NkTxU6kiwBgiwHw-5FA","agent_name":"expire-test-agent","session_file":"/Users/kc/.pi/agent/sessions/managed/expire-test-agent/B1sqGBZ0QWMxMyojbrLVYg.jsonl","status":"completed","turns":0,"tokens_in":0,"tokens_out":0,"model":"sonnet","started_at":"2026-06-12T18:06:50.035588+00:00","ended_at":"2026-06-12T18:06:52.543095+00:00"},{"id":"sXq9YNXJ_mItpLzLatmuxA","agent_id":"QI5NkTxU6kiwBgiwHw-5FA","agent_na
## skills
{"skills":[{"name":"adr","description":"Write an Architecture Decision Record — document a decision so future-you understands why","location":"/Users/kc/.pi/agent/skills/adr","inputs":{},"outputs":{},"triggers":[]},{"name":"agentic-core","description":"Sovereign Pi Agentic Layer Master Orchestrator. Single entrypoint for all complex work in dabasemint and everywhere else. Routes intelligently to ultraplan, karpathy-discipline, fairy-tales chains (feature-ship, bughunt, heal, onboard, research, release, migrate), multi-agent-maestro, subagents, graphify, and all specialized skills. Maintains persistent project memory and knowledge graph. Uses the global ~/.pi everywhere.","location":"/Users/kc/.pi/agent/skills/agentic-core","inputs":{},"outputs":{},"triggers":[]},{"name":"agentic-enable",
## telemetry
{"cpu":{"percent":35.0,"count":8},"memory":{"total_gb":8.0,"used_gb":3.4,"available_gb":1.7,"percent":78.6},"disk":{"total_gb":228.3,"used_gb":180.4,"free_gb":9.1,"percent":95.2},"hostname":"kcs-MacBook-Air-5.local"}
## delete agent
{"status":"deleted","agent_id":"3U6NPv6xCngXuH5VNkLiTg"}

---

## Conclusions (orchestrator)

| Check | Result |
|-------|--------|
| Server start | OK on 127.0.0.1:8420 |
| `/health` | `status=ok` |
| OpenAPI `/docs` | 200 |
| SPA `/` | 200 |
| Agent create/get/delete | OK |
| Real pi chat | SSE `text_delta` content `pong` (pi 0.80.7) |
| Sessions list | OK (includes new session) |
| Skills / telemetry | OK |
| Teardown | OK |

**Verdict:** Core local operator path is **live and functional** at SHA `9249dfa`.
