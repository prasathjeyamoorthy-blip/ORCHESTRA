export async function sendMessage(sessionId, message) {
  const res = await fetch(`${import.meta.env.VITE_API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
    }),
  });

  if (!res.ok) {
    let detail = `Backend error ${res.status}`;
    try {
      const body = await res.json();
      if (body.error) detail = body.error;
    } catch (_) {}
    throw new Error(detail);
  }

  return res.json();
}
