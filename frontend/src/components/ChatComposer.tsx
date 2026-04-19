import { FormEvent, KeyboardEvent, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";

interface ChatComposerProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const ChatComposer = ({ onSend, disabled }: ChatComposerProps) => {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={submit}
      className="border-t border-border bg-background/90 backdrop-blur-md px-3 py-3"
    >
      <div className="max-w-3xl mx-auto flex items-end gap-2 rounded-3xl border border-border bg-card shadow-soft px-3 py-2 focus-within:ring-2 focus-within:ring-ring transition-smooth">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            const tEl = e.target as HTMLTextAreaElement;
            tEl.style.height = "auto";
            tEl.style.height = Math.min(tEl.scrollHeight, 160) + "px";
          }}
          onKeyDown={handleKey}
          placeholder={t("chat.placeholder")}
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-sm leading-relaxed py-2 px-1 outline-none placeholder:text-muted-foreground max-h-40"
          aria-label={t("chat.inputAria")}
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !value.trim()}
          className="rounded-full h-10 w-10 bg-gradient-primary shrink-0 shadow-soft"
          aria-label={t("chat.send")}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <p className="text-[11px] text-muted-foreground text-center mt-2 max-w-3xl mx-auto">
        {t("chat.footerNote")}
      </p>
    </form>
  );
};

export default ChatComposer;
