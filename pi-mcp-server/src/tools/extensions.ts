export function extensionsListTool(baseUrl: string) {
  return async () => {
    const res = await fetch(`${baseUrl}/api/extensions`);
    const data = await res.json();
    return {
      content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    };
  };
}
