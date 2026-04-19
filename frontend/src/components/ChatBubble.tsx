import { cn } from "@/lib/utils";
import { Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatBubbleProps {
  role: "user" | "assistant";
  content: string;
  shredding?: boolean;
}

/** Assistant replies often include Markdown (**bold**, lists); user text stays plain. */
const assistantMarkdownClass =
  "prose prose-sm max-w-none text-card-foreground " +
  "prose-headings:font-semibold prose-headings:text-card-foreground " +
  "prose-p:my-2 prose-p:leading-relaxed prose-strong:text-card-foreground prose-strong:font-semibold " +
  "prose-a:text-primary prose-a:font-medium prose-a:no-underline hover:prose-a:underline " +
  "prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 " +
  "prose-blockquote:border-l-primary prose-blockquote:text-muted-foreground " +
  "dark:prose-invert dark:prose-headings:text-card-foreground";

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
        {isUser ? (
          <span className="whitespace-pre-wrap break-words">{content}</span>
        ) : (
          <ReactMarkdown
            className={assistantMarkdownClass}
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node: _n, ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" />
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;
