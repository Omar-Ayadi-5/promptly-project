export async function readAIResponse(response) {
  const data = await response.json().catch(() => null);
  if (!response.ok || data?.error) {
    const detail = typeof data?.error === 'string' ? data.error : data?.error?.message;
    throw new Error(detail || `Failed to get an AI response (HTTP ${response.status}).`);
  }
  if (typeof data?.response !== 'string' || !data.response.trim()) {
    throw new Error('The model returned an empty answer. Try again or select another model.');
  }
  return data.response;
}
