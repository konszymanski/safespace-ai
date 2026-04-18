// Mock klient API — symuluje endpoint Osoby 2.
// Zastąp wywołanie `fetch` realnym endpointem, gdy API będzie gotowe.
import i18n from "@/i18n";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

interface EmergencyLine {
  number: string;
  label: string;
}

// Słowa kluczowe dla detekcji kryzysu w trzech językach
const CRISIS_PATTERNS: Record<string, RegExp> = {
  pl: /(samob|skrzywdz|zabi[ćj]|nie chcę żyć|nie chce zyc|targn|odebra[ćc] sobie życie)/i,
  en: /(suicid|kill myself|end my life|self[- ]?harm|hurt myself|don'?t want to live|want to die)/i,
  uk: /(самогубств|вбити себе|накласти на себе руки|не хочу жити|завдати собі|покінчити|самопошкодж)/i,
};

function matchesCrisis(text: string, lang: string): boolean {
  const base = (lang || "pl").split("-")[0];
  const patterns = [CRISIS_PATTERNS[base], CRISIS_PATTERNS.pl, CRISIS_PATTERNS.en, CRISIS_PATTERNS.uk];
  return patterns.some((p) => p?.test(text));
}

export async function sendMessageMock(history: ChatMessage[]): Promise<string> {
  // Symulacja opóźnienia sieci
  await new Promise((r) => setTimeout(r, 900 + Math.random() * 800));

  const lang = i18n.language || "pl";
  const last = history[history.length - 1]?.content ?? "";

  const lines = (i18n.t("emergency.lines", { returnObjects: true }) as EmergencyLine[]) ?? [];
  const emergency = lines[0]?.number ?? "112";
  const trustline = lines[1]?.number ?? lines[0]?.number ?? "112";

  if (matchesCrisis(last, lang)) {
    return i18n.t("mock.crisis", { emergency, trustline });
  }

  const replies = (i18n.t("mock.replies", { returnObjects: true }) as string[]) ?? [];
  if (replies.length === 0) {
    return i18n.t("chat.greeting");
  }
  return replies[Math.floor(Math.random() * replies.length)];
}
