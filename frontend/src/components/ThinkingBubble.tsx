import { useTranslation } from "react-i18next";
import { Sparkles } from "lucide-react";

const ThinkingBubble = () => {
  const { t } = useTranslation();
  return (
    <div className="flex w-full gap-2 animate-fade-in" aria-live="polite" aria-label={t("chat.thinkingAria")}>
      <div className="h-8 w-8 rounded-full bg-gradient-primary flex items-center justify-center shrink-0 shadow-soft">
        <Sparkles className="h-4 w-4 text-primary-foreground" />
      </div>
      <div className="bg-card border border-border rounded-3xl rounded-bl-md px-4 py-3 shadow-soft flex items-center gap-2">
        <span className="text-xs text-muted-foreground">{t("chat.thinking")}</span>
        <span className="flex items-end gap-1 h-3">
          <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-primary" style={{ animationDelay: "0s" }} />
          <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-primary" style={{ animationDelay: "0.15s" }} />
          <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-primary" style={{ animationDelay: "0.3s" }} />
        </span>
      </div>
    </div>
  );
};

export default ThinkingBubble;
