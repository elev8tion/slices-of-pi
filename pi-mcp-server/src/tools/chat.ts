export function chatSendTool(baseUrl: string) {
  return async (args: { agent_id: string; message: string }) => {
    const res = await fetch(`${baseUrl}/api/agents/${args.agent_id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: args.message }),
    });
    const text = await res.text();
    return {
      content: [{ type: "text", text }],
    };
  };
}
