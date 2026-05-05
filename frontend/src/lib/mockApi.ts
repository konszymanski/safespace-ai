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

// Komunikat „źle odczytałeś moje emocje" — wysyłany przyciskiem w UI
const MISREAD_PATTERNS: RegExp[] = [
  /to nie to, o co mi chodziło/i,
  /that's not what i meant/i,
  /це не те, що я мав/i,
];

const MISREAD_REPLIES: Record<string, string> = {
  pl: "Dziękuję, że mi to mówisz — masz rację, nie chcę zakładać. Resetuję to, co zrozumiałem do tej pory. Powiedz mi własnymi słowami, co teraz w tobie jest — bez konieczności nazywania tego „poprawnie”.",
  en: "Thank you for telling me — you're right, I shouldn't assume. I'm resetting what I thought I understood. Tell me in your own words what's actually going on inside you right now — no need to name it „correctly”.",
  uk: "Дякую, що сказав(ла) це — твоя правда, не буду припускати. Скидаю те, що, як мені здавалося, я зрозумів. Розкажи своїми словами, що насправді зараз у тобі — не треба називати це „правильно”.",
};

function matchesMisread(text: string): boolean {
  return MISREAD_PATTERNS.some((p) => p.test(text));
}

/** Zwraca tylko treść odpowiedzi — wygodnie do testów / prostych wywołań. */

export async function sendMessageMock(history: ChatMessage[]): Promise<string> {

  const r = await sendChatMessage(history);

  const last = history[history.length - 1]?.content ?? "";
  const lang = i18n.language || "en";
  if (matchesMisread(last)) {
    const base = lang.split("-")[0];
    return MISREAD_REPLIES[base] ?? MISREAD_REPLIES.pl;
  }

  return r.assistant_reply;

}

