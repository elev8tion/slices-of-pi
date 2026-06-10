export function schedulesListTool(baseUrl: string) {
  return async () => {
    const res = await fetch(`${baseUrl}/api/schedules`);
    const schedules = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(schedules, null, 2) }],
    };
  };
}

export function scheduleCreateTool(baseUrl: string) {
  return async (args: { agent_id: string; cron: string; message: string }) => {
    const res = await fetch(`${baseUrl}/api/schedules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: args.agent_id,
        cron_expression: args.cron,
        message: args.message,
      }),
    });
    const schedule = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(schedule, null, 2) }],
    };
  };
}
