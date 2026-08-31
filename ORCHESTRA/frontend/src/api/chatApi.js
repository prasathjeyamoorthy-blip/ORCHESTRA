import { encryptPayloadZK, decryptPayload } from "../utils/crypto";

export async function sendMessage(sessionId, message, phoneNumber = "", language = "en") {
  let encryptedContent = message;
  if (phoneNumber) {
    try {
      encryptedContent = await encryptPayloadZK(message, phoneNumber);
    } catch (e) {
      console.warn("[chatApi] Zero-knowledge client encryption warning:", e);
    }
  }

  const res = await fetch(`${import.meta.env.VITE_API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
      phone_number: phoneNumber,
      language: language,
      encrypted_content: encryptedContent,
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

export async function sendMessageStream(sessionId, message, phoneNumber = "", language = "en", onToken = null) {
  let encryptedContent = message;
  if (phoneNumber) {
    try {
      encryptedContent = await encryptPayloadZK(message, phoneNumber);
    } catch (e) {
      console.warn("[chatApi] Zero-knowledge client encryption warning:", e);
    }
  }

  const res = await fetch(`${import.meta.env.VITE_API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
      phone_number: phoneNumber,
      language: language,
      encrypted_content: encryptedContent,
    }),
  });

  if (!res.ok) {
    let detail = `Backend streaming error ${res.status}`;
    try {
      const body = await res.json();
      if (body.error) detail = body.error;
    } catch (_) {}
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let doneReading = false;
  let fullText = "";
  let lastStage = null;
  let lastCategory = null;

  while (!doneReading) {
    const { value, done } = await reader.read();
    doneReading = done;
    if (value) {
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);
          if (data.stage) lastStage = data.stage;
          if (data.category) lastCategory = data.category;
          if (data.token) {
            fullText += data.token;
            if (onToken) onToken(data.token, fullText);
          }
          if (data.done) {
            return {
              answer: data.answer || fullText,
              stage: data.stage || lastStage,
              category: data.category || lastCategory
            };
          }
        } catch (_) {}
      }
    }
  }

  return { answer: fullText, stage: lastStage, category: lastCategory };
}

export async function fetchChatHistoryApi(phoneNumber) {
  const res = await fetch(
    `${import.meta.env.VITE_API_BASE}/api/chat-history?phone_number=${encodeURIComponent(phoneNumber)}`
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch history (${res.status})`);
  }
  const data = await res.json();

  if (data && Array.isArray(data.history)) {
    data.history = await Promise.all(
      data.history.map(async (item) => ({
        ...item,
        content: await decryptPayload(item.content, phoneNumber),
      }))
    );
  }

  return data;
}

export async function deleteChatHistoryApi(phoneNumber, sessionId = null) {
  let url = `${import.meta.env.VITE_API_BASE}/api/chat-history?phone_number=${encodeURIComponent(phoneNumber)}`;
  if (sessionId) {
    url += `&session_id=${encodeURIComponent(sessionId)}`;
  }
  const res = await fetch(url, {
    method: "DELETE",
  });
  if (!res.ok) {
    let detail = `Failed to delete chat history (${res.status})`;
    try {
      const body = await res.json();
      if (body.error) detail = body.error;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}


export async function sendOtpApi(phoneNumber) {
  const res = await fetch(`${import.meta.env.VITE_API_BASE}/api/send-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
  const data = await res.json();
  if (!res.ok || !data.success) {
    throw new Error(data.message || `Failed to send OTP (${res.status})`);
  }
  return data;
}

export async function verifyOtpApi(phoneNumber, code, verificationId) {
  const res = await fetch(`${import.meta.env.VITE_API_BASE}/api/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      phone_number: phoneNumber,
      code: code,
      verification_id: verificationId,
    }),
  });
  const data = await res.json();
  if (!res.ok || !data.success) {
    throw new Error(data.message || `Invalid OTP code (${res.status})`);
  }
  return data;
}
