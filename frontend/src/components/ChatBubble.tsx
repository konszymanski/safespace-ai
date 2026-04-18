import { cn } from "@/lib/utils";
import { Sparkles } from "lucide-react";

interface ChatBubbleProps {
  role: "user" | "assistant";
  content: string;
  shredding?: boolean;
}

const ChatBubble = ({ role, content, shredding }: ChatBubbleProps) => {
  const isUser = role === "user";
  return (
    <div
      className={cn(
        "flex w-full gap-2 animate-fade-in",
        isUser ? "justify-end" : "justify-start",
        shredding && "animate-shred",
      )}
    >
      {!isUser && (
        <div className="h-8 w-8 rounded-full bg-gradient-primary flex items-center justify-center shrink-0 shadow-soft">
          <Sparkles className="h-4 w-4 text-primary-foreground" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[78%] px-4 py-3 text-sm leading-relaxed shadow-soft",
          isUser
            ? "bg-primary text-primary-foreground rounded-3xl rounded-br-md"
            : "bg-card text-card-foreground rounded-3xl rounded-bl-md border border-border",
        )}
      >
        {content}
      </div>
    </div>
  );
};

export default ChatBubble;
