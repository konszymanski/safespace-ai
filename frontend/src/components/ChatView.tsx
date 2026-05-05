import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { toast } from "sonner";
import ChatBubble from "./ChatBubble";
import ChatComposer from "./ChatComposer";
import ExportChatPrompt from "./ExportChatPrompt";
import ThinkingBubble from "./ThinkingBubble";
import {
  type ChatMessage,
  revokeCurrentChatSession,
  sendChatMessage,
} from "@/lib/mockApi";

interface ChatViewProps {
  shreddingTick: number;
}

// Wybiera losowe pytanie startowe z bazy ~36 uniwersalnych otwarć
const pickStarter = (t: TFunction): string => {
  const list = (t("starters", { returnObjects: true }) as unknown) as string[];
  if (!Array.isArray(list) || list.length === 0) {
    return t("chat.greeting");
  }
  return list[Math.floor(Math.random() * list.length)];
};

const ChatView = ({ shreddingTick }: ChatViewProps) => {
  const { t, i18n } = useTranslation();

  // Pierwsze pytanie wybierane raz przy inicjalizacji widoku
  const initialMessage = useMemo<ChatMessage>(
    () => ({ role: "assistant", content: pickStarter(t) }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage]);
  const [thinking, setThinking] = useState(false);
  const [shredding, setShredding] = useState(false);
  const [exportPromptDismissed, setExportPromptDismissed] = useState(false);
  // True dopóki użytkownik nic nie napisał — pozwala odświeżyć powitanie po zmianie języka
  const [untouched, setUntouched] = useState(true);
  const [interactionStartTime, setInteractionStartTime] = useState<Date | null>(null);
  const [breakSuggested, setBreakSuggested] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Po zmianie języka wylosuj nowe powitanie, jeśli rozmowa jeszcze się nie zaczęła
  useEffect(() => {
    if (untouched) {
      setMessages([{ role: "assistant", content: pickStarter(t) }]);
    }
  }, [i18n.language, t, untouched]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  // Timer dla sugestii przerwy po 30 minutach interakcji
  useEffect(() => {
    if (interactionStartTime && !breakSuggested) {
      const timer = setTimeout(() => {
        const breakMessage: ChatMessage = {
          role: "assistant",
          content: t("chat.breakSuggestion", {
            defaultValue: "Wygląda na to, że rozmawiamy już jakiś czas. Może warto zrobić przerwę? Pamiętaj, że zawsze możesz porozmawiać z prawdziwym człowiekiem, jeśli potrzebujesz wsparcia. Jak się czujesz?"
          })
        };
        setMessages(prev => [...prev, breakMessage]);
        setBreakSuggested(true);
      }, 30 * 60 * 1000); // 30 minut
      return () => clearTimeout(timer);
    }
  }, [interactionStartTime, breakSuggested, t]);

  useEffect(() => {
    if (shreddingTick === 0) return;
    setShredding(true);
    void revokeCurrentChatSession();
    const timer = setTimeout(() => {
      setMessages([{ role: "assistant", content: pickStarter(t) }]);
      setUntouched(true);
      setExportPromptDismissed(false);
      setShredding(false);
      toast.success(t("chat.cleared"), {
        description: t("chat.clearedDesc"),
      });
    }, 1100);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shreddingTick]);

  const handleMisread = () => {
    // Dodaj wiadomość informującą o błędnym rozpoznaniu
    const misreadMessage: ChatMessage = {
      role: "user",
      content: "To nie to, o co mi chodziło. Proszę o reset kontekstu emocjonalnego."
    };
    setMessages(prev => [...prev, misreadMessage]);
    // Opcjonalnie, zresetuj timer lub coś
    setBreakSuggested(false);
    setInteractionStartTime(null);
  };

  const handleSend = async (text: string) => {
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setUntouched(false);
    if (!interactionStartTime) {
      setInteractionStartTime(new Date());
    }
    setThinking(true);
    try {
      const payload = await sendChatMessage(next);
      setMessages((m) => [...m, { role: "assistant", content: payload.assistant_reply }]);
    } catch {
      toast.error(t("chat.error"));
    } finally {
      setThinking(false);
    }
  };

  return (
    <main className="flex-1 flex flex-col min-h-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-6" aria-live="polite">
        <div className="max-w-3xl mx-auto flex flex-col gap-4">
          {messages.map((m, i) => (
            <ChatBubble
              key={i}
              role={m.role}
              content={m.content}
              shredding={shredding && i > 0}
              showMisreadAction={m.role === "assistant" && i > 0}
              onMisread={handleMisread}
            />
          ))}
          {thinking && <ThinkingBubble />}
        </div>
      </div>
      <ChatComposer onSend={handleSend} disabled={thinking || shredding} />
      <ExportChatPrompt
        messages={messages}
        dismissed={exportPromptDismissed}
        shredding={shredding}
        onDismiss={() => setExportPromptDismissed(true)}
      />
    </main>
  );
};

export default ChatView;