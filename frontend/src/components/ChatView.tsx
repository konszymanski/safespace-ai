import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import ChatBubble from "./ChatBubble";
import ChatComposer from "./ChatComposer";
import ThinkingBubble from "./ThinkingBubble";
import { ChatMessage, revokeCurrentChatSession, sendMessageMock } from "@/lib/mockApi";

interface ChatViewProps {
  shreddingTick: number;
}

const ChatView = ({ shreddingTick }: ChatViewProps) => {
  const { t, i18n } = useTranslation();

  const initialMessage = useMemo<ChatMessage>(
    () => ({ role: "assistant", content: t("chat.greeting") }),
    [t, i18n.language],
  );

  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage]);
  const [thinking, setThinking] = useState(false);
  const [shredding, setShredding] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Aktualizuj powitanie po zmianie języka, jeśli to wciąż jedyna wiadomość
  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].role === "assistant") {
        return [{ role: "assistant", content: t("chat.greeting") }];
      }
      return prev;
    });
  }, [i18n.language, t]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  useEffect(() => {
    if (shreddingTick === 0) return;
    setShredding(true);
    const timer = setTimeout(() => {
      void (async () => {
        await revokeCurrentChatSession();
        setMessages([{ role: "assistant", content: t("chat.greeting") }]);
        setShredding(false);
        toast.success(t("chat.cleared"), {
          description: t("chat.clearedDesc"),
        });
      })();
    }, 1100);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shreddingTick]);

  const handleSend = async (text: string) => {
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setThinking(true);
    try {
      const reply = await sendMessageMock(next);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
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
            <ChatBubble key={i} role={m.role} content={m.content} shredding={shredding && i > 0} />
          ))}
          {thinking && <ThinkingBubble />}
        </div>
      </div>
      <ChatComposer onSend={handleSend} disabled={thinking || shredding} />
    </main>
  );
};

export default ChatView;
