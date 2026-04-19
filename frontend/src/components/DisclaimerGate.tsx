import { useEffect, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ShieldCheck, PhoneCall, HeartHandshake } from "lucide-react";
import LanguageSwitcher from "./LanguageSwitcher";

const STORAGE_KEY = "safespace.consent.v1";

interface DisclaimerGateProps {
  onAccept: () => void;
}

interface EmergencyLine {
  number: string;
  label: string;
}

const DisclaimerGate = ({ onAccept }: DisclaimerGateProps) => {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(true);
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(STORAGE_KEY) === "1") {
      setOpen(false);
      onAccept();
    }
  }, [onAccept]);

  const handleAccept = () => {
    sessionStorage.setItem(STORAGE_KEY, "1");
    setOpen(false);
    onAccept();
  };

  if (!open) return null;

  const lines = (t("emergency.lines", { returnObjects: true }) as EmergencyLine[]) ?? [];
  const country = t("emergency.country");
  const primaryEmergency = lines[0]?.number ?? "112";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="disclaimer-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-md p-4 animate-fade-in"
      key={i18n.language}
    >
      <div className="w-full max-w-lg rounded-3xl bg-card shadow-soft border border-border overflow-hidden animate-scale-in">
        <div className="bg-gradient-primary px-6 py-5 text-primary-foreground flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs uppercase tracking-wider opacity-90">{t("disclaimer.kicker")}</p>
            <h2 id="disclaimer-title" className="font-display text-2xl leading-tight">
              {t("disclaimer.title")}
            </h2>
          </div>
          <div className="shrink-0 -mr-2">
            <LanguageSwitcher />
          </div>
        </div>

        <div className="px-6 py-5 space-y-4 text-sm leading-relaxed text-foreground">
          <p>
            <strong>{t("disclaimer.notMedical")}</strong> {t("disclaimer.intro")}
          </p>

          <div className="rounded-2xl bg-secondary p-4 space-y-2">
            <div className="flex items-center justify-between gap-2 text-secondary-foreground font-medium">
              <span className="flex items-center gap-2">
                <PhoneCall className="h-4 w-4" />
                {t("disclaimer.needHelpNow")}
              </span>
              <span className="text-xs font-normal opacity-75">{country}</span>
            </div>
            <ul className="space-y-1 text-secondary-foreground/90">
              {lines.map((line, i) => (
                <li key={i}>
                  • <strong>{line.number}</strong> — {line.label}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-start gap-2 text-muted-foreground">
            <HeartHandshake className="h-4 w-4 mt-0.5 shrink-0" />
            <p>{t("disclaimer.privacyNote")}</p>
          </div>

          <label className="flex items-start gap-3 cursor-pointer select-none rounded-xl p-3 hover:bg-muted transition-smooth">
            <Checkbox
              checked={agreed}
              onCheckedChange={(v) => setAgreed(v === true)}
              className="mt-0.5"
              aria-label={t("disclaimer.consentAria")}
            />
            <span className="text-sm text-foreground">
              <Trans
                i18nKey="disclaimer.consent"
                values={{ emergency: primaryEmergency }}
                components={{ strong: <strong /> }}
              />
            </span>
          </label>
        </div>

        <div className="px-6 pb-6">
          <Button
            onClick={handleAccept}
            disabled={!agreed}
            className="w-full h-12 rounded-2xl bg-gradient-primary hover:opacity-95 transition-smooth text-base"
          >
            {t("disclaimer.accept")}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default DisclaimerGate;
