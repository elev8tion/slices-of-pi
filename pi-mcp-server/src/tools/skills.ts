export function skillsListTool(baseUrl: string) {
  return async () => {
    const res = await fetch(`${baseUrl}/api/skills`);
    const data = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    };
  };
}
