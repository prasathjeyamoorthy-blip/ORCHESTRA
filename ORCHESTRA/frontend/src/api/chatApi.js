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
    throw new Error("Backend error");
  }

  return res.json();
}
