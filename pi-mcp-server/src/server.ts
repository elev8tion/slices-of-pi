/**
 * Pi MCP Server — expose pi orchestrator capabilities as MCP tools.
 *
 * STDIO transport for direct integration (Claude Desktop, pi, etc.).
 * 10 tools: agents, chat, sessions, skills, extensions, schedules.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const ORCHESTRATOR_URL = process.env.PI_ORCHESTRATOR_URL || "http://127.0.0.1:8420";

async function api(path: string, opts?: RequestInit) {
  const res = await fetch(`${ORCHESTRATOR_URL}${path}`, opts);
  return res.json();
}

const server = new McpServer({
  name: "pi-orchestrator",
  version: "0.1.0",
});

// Agents — no params = empty object schema
server.tool("pi_agents_list", "List all managed pi agents", {},
  async () => ({ content: [{ type: "text" as const, text: JSON.stringify(await api("/api/agents"), null, 2) }] })
);

server.tool("pi_agent_create", "Create a new pi agent",
  { name: z.string(), model: z.string().optional() },
  async (args) => ({
    content: [{ type: "text" as const, text: JSON.stringify(await api("/api/agents", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: args.name, model: args.model || "claude-sonnet-4-5" }),
    }), null, 2) }]
  })
);

server.tool("pi_agent_delete", "Stop and remove an agent",
  { agent_id: z.string() },
  async (args) => ({
    content: [{ type: "text" as const, text: JSON.stringify(await api(`/api/agents/${args.agent_id}`, { method: "DELETE" }), null, 2) }]
  })
);

// Chat
server.tool("pi_chat_send", "Send a message to an agent and stream response",
  { agent_id: z.string(), message: z.string() },
  async (args) => {
    const res = await fetch(`${ORCHESTRATOR_URL}/api/agents/${args.agent_id}/chat`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: args.message }),
    });
    return { content: [{ type: "text" as const, text: await res.text() }] };
  }
);

// Sessions
server.tool("pi_sessions_list", "List recent sessions", {},
  async () => ({ content: [{ type: "text" as const, text: JSON.stringify(await api("/api/sessions"), null, 2) }] })
);

server.tool("pi_session_get", "Get session details with messages",
  { session_id: z.string() },
  async (args) => ({
    content: [{ type: "text" as const, text: JSON.stringify(await api(`/api/sessions/${args.session_id}`), null, 2) }]
  })
);

// Skills
server.tool("pi_skills_list", "List installed pi skills with descriptions", {},
  async () => ({ content: [{ type: "text" as const, text: JSON.stringify(await api("/api/skills"), null, 2) }] })
);

// Extensions
server.tool("pi_extensions_list", "List installed pi extensions", {},
  async () => ({ content: [{ type: "text" as const, text: JSON.stringify(await api("/api/extensions"), null, 2) }] })
);

// Schedules
server.tool("pi_schedules_list", "List cron schedules", {},
  async () => ({ content: [{ type: "text" as const, text: JSON.stringify(await api("/api/schedules"), null, 2) }] })
);

server.tool("pi_schedule_create", "Create a recurring schedule",
  { agent_id: z.string(), cron: z.string(), message: z.string() },
  async (args) => ({
    content: [{ type: "text" as const, text: JSON.stringify(await api("/api/schedules", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: args.agent_id, cron_expression: args.cron, message: args.message }),
    }), null, 2) }]
  })
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
