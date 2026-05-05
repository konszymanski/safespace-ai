import { cn } from "@/lib/utils";

import { Sparkles, RefreshCcw, AlertTriangle } from "lucide-react";

import ReactMarkdown from "react-markdown";

import remarkGfm from "remark-gfm";



interface ChatBubbleProps {

  role: "user" | "assistant";

  content: string;

  shredding?: boolean;

  /** Pokaż przycisk „to nie to, o co mi chodziło” pod dymkiem AI */
  showMisreadAction?: boolean;
  onMisread?: () => void;

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



const ChatBubble = ({ role, content, shredding, showMisreadAction, onMisread }: ChatBubbleProps) => {

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

      {showMisreadAction && !isUser && (
        <button
          onClick={onMisread}
          className="mt-2 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          title="To nie to, o co mi chodziło"
        >
          <AlertTriangle className="h-3 w-3" />
          To nie to, o co mi chodziło
        </button>
      )}
    </div>

  );

};



export default ChatBubble;

