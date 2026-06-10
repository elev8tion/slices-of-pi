export function agentsListTool(baseUrl: string) {
  return async () => {
    const res = await fetch(`${baseUrl}/api/agents`);
    const agents = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(agents, null, 2) }],
    };
  };
}

export function agentCreateTool(baseUrl: string) {
  return async (args: { name: string; model?: string; tools?: string }) => {
    const res = await fetch(`${baseUrl}/api/agents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: args.name,
        model: args.model || "claude-sonnet-4-5",
        tools: args.tools ? args.tools.split(",") : undefined,
      }),
    });
    const agent = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(agent, null, 2) }],
    };
  };
}

export function agentStartTool(baseUrl: string) {
  return async () => ({
    content: [{ type: "text", text: "Use pi_chat_send to start a conversation" }],
  });
}

export function agentStopTool(baseUrl: string) {
  return async (args: { agent_id: string }) => {
    const res = await fetch(`${baseUrl}/api/agents/${args.agent_id}`, { method: "DELETE" });
    const result = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  };
}
