import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { DoorOpen, Trash2, ShieldCheck } from "lucide-react";
import LanguageSwitcher from "./LanguageSwitcher";

interface QuickExitBarProps {
  onShred: () => void;
}

const QuickExitBar = ({ onShred }: QuickExitBarProps) => {
  const { t } = useTranslation();

  const handleQuickExit = () => {
    try {
      sessionStorage.clear();
    } catch {
      /* noop */
    }
    window.location.replace("https://www.google.com/search?q=weather");
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-border bg-background/85 backdrop-blur-md">
      <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-8 w-8 rounded-xl bg-gradient-primary flex items-center justify-center shrink-0 shadow-soft">
            <ShieldCheck className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="min-w-0">
            <p className="font-display text-base leading-none truncate">{t("header.title")}</p>
            <p className="text-[11px] text-muted-foreground leading-tight">{t("header.tagline")}</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <LanguageSwitcher />

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onShred}
            className="rounded-full text-muted-foreground hover:text-foreground"
            aria-label={t("header.clearAria")}
          >
            <Trash2 className="h-4 w-4 sm:mr-1.5" />
            <span className="hidden sm:inline">{t("header.clear")}</span>
          </Button>

          <Button
            type="button"
            onClick={handleQuickExit}
            size="sm"
            className="rounded-full bg-danger hover:bg-danger/90 text-danger-foreground animate-soft-pulse"
            aria-label={t("header.quickExitAria")}
          >
            <DoorOpen className="h-4 w-4 mr-1.5" />
            {t("header.quickExit")}
          </Button>
        </div>
      </div>
    </header>
  );
};

export default QuickExitBar;
