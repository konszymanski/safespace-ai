import { useTranslation } from "react-i18next";
import { Globe } from "lucide-react";
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "@/i18n";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

const FLAGS: Record<SupportedLanguage, string> = {
  pl: "🇵🇱",
  en: "🇬🇧",
  uk: "🇺🇦",
};

const LanguageSwitcher = () => {
  const { t, i18n } = useTranslation();
  const current = (i18n.resolvedLanguage ?? i18n.language ?? "pl").split("-")[0] as SupportedLanguage;
  const safeCurrent = SUPPORTED_LANGUAGES.includes(current) ? current : "pl";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="rounded-full text-muted-foreground hover:text-foreground gap-1.5"
          aria-label={t("language.label")}
        >
          <Globe className="h-4 w-4" />
          <span className="text-sm" aria-hidden="true">{FLAGS[safeCurrent]}</span>
          <span className="hidden sm:inline text-xs uppercase tracking-wider">
            {safeCurrent}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="rounded-2xl">
        {SUPPORTED_LANGUAGES.map((lng) => {
          const isDisabled = lng !== "en";
          return (
            <DropdownMenuItem
              key={lng}
              disabled={isDisabled}
              onSelect={(e) => {
                if (isDisabled) {
                  e.preventDefault();
                  return;
                }
                i18n.changeLanguage(lng);
              }}
              className="rounded-xl gap-2 cursor-pointer data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 data-[disabled]:text-muted-foreground"
              aria-current={lng === safeCurrent ? "true" : undefined}
            >
              <span aria-hidden="true">{FLAGS[lng]}</span>
              <span className="flex-1">{t(`language.${lng}`)}</span>
              {lng === safeCurrent && (
                <span className="text-xs text-primary">●</span>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default LanguageSwitcher;