// Klient API dla czatu backendowego.
import i18n from "@/i18n";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatApiResponse = {
  assistant_reply: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";

export async function sendMessageMock(history: ChatMessage[]): Promise<string> {
  const last = history[history.length - 1]?.content?.trim() ?? "";
  if (!last) {
    return i18n.t("chat.greeting");
  }

  const sessionId =
    localStorage.getItem("chat_session_id") ?? `session-${crypto.randomUUID()}`;
  localStorage.setItem("chat_session_id", sessionId);

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      message: last,
    }),
  });

  if (!response.ok) {
    throw new Error(`Backend error: ${response.status}`);
  }

  const payload = (await response.json()) as ChatApiResponse;
  return payload.assistant_reply ?? i18n.t("chat.greeting");
}
