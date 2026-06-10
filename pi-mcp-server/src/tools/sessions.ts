export function sessionsListTool(baseUrl: string) {
  return async () => {
    const res = await fetch(`${baseUrl}/api/sessions`);
    const sessions = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(sessions, null, 2) }],
    };
  };
}

export function sessionGetTool(baseUrl: string) {
  return async (args: { session_id: string }) => {
    const res = await fetch(`${baseUrl}/api/sessions/${args.session_id}`);
    const session = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(session, null, 2) }],
    };
  };
}
