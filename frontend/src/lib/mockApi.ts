// Klient API dla czatu backendowego.

import i18n from "@/i18n";



/** Odpowiednik `classifier.xai` z POST /chat (backend nadal może zwracać — UI go nie pokazuje). */

export type ChatXaiSentence = {

  sentence_text: string;

  sentence_risk: number;

  top_dangerous_words: { word: string; impact: number }[];

};



export type ChatXaiPayload = {

  top_risk_analysis?: ChatXaiSentence[];

  overall_text?: string;

} | null;



export type ChatMessage = {

  role: "user" | "assistant";

  content: string;

};



export type ChatApiPayload = {

  assistant_reply: string;

  safety_mode: string;

  classifier?: {

    xai?: ChatXaiPayload;

    [key: string]: unknown;

  };

};



const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";



const CHAT_SESSION_ID_KEY = "chat_session_id";



/** Clears only the browser id; next message creates a new session_id. */

export function clearChatSessionId(): void {

  try {

    localStorage.removeItem(CHAT_SESSION_ID_KEY);

  } catch {

    /* private mode / blocked storage */

  }

}



/** Best-effort: remove server RAM for this session, then clear local id. */

export async function revokeCurrentChatSession(): Promise<void> {

  let id: string | null = null;

  try {

    id = localStorage.getItem(CHAT_SESSION_ID_KEY);

  } catch {

    /* noop */

  }

  if (id) {

    try {

      await fetch(`${API_BASE_URL}/session/${encodeURIComponent(id)}`, {

        method: "DELETE",

      });

    } catch {

      /* offline / CORS — still drop local id */

    }

  }

  clearChatSessionId();

}



export async function sendChatMessage(history: ChatMessage[]): Promise<ChatApiPayload> {

  const last = history[history.length - 1]?.content?.trim() ?? "";

  if (!last) {

    return {

      assistant_reply: i18n.t("chat.greeting"),

      safety_mode: "NORMAL",

    };

  }



  const sessionId =

    localStorage.getItem(CHAT_SESSION_ID_KEY) ?? `session-${crypto.randomUUID()}`;

  localStorage.setItem(CHAT_SESSION_ID_KEY, sessionId);



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



  const payload = (await response.json()) as ChatApiPayload;

  return {

    assistant_reply: payload.assistant_reply ?? i18n.t("chat.greeting"),

    safety_mode: payload.safety_mode ?? "NORMAL",

    classifier: payload.classifier,

  };

}



/** Zwraca tylko treść odpowiedzi — wygodnie do testów / prostych wywołań. */

export async function sendMessageMock(history: ChatMessage[]): Promise<string> {

  const r = await sendChatMessage(history);

  return r.assistant_reply;

}

