import { useTranslation } from "react-i18next";
import { Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChatMessage } from "@/lib/mockApi";
import { buildChatExportText, downloadTextFile, exportChatFilename } from "@/lib/exportChat";
import { toast } from "sonner";

const MIN_USER_MESSAGES = 2;

interface ExportChatPromptProps {
  messages: ChatMessage[];
  dismissed: boolean;
  shredding: boolean;
  onDismiss: () => void;
}

const ExportChatPrompt = ({ messages, dismissed, shredding, onDismiss }: ExportChatPromptProps) => {
  const { t } = useTranslation();
  const userTurns = messages.filter((m) => m.role === "user").length;
  const visible = userTurns >= MIN_USER_MESSAGES && !dismissed && !shredding;

  if (!visible) return null;

  const handleDownload = () => {
    const header = [
      t("chat.exportTitle"),
      `${t("chat.exportGenerated")}: ${new Date().toLocaleString()}`,
    ];
    const body = buildChatExportText(
      messages,
      header,
      { user: t("chat.exportRoleUser"), assistant: t("chat.exportRoleAssistant") },
      t("chat.exportFooter"),
    );
    downloadTextFile(body, exportChatFilename());
    toast.success(t("chat.exportDone"));
  };

  return (
    <div
      className="fixed z-40 w-[min(100vw-1.5rem,20rem)] bottom-24 right-3 sm:right-6 animate-fade-in"
      role="dialog"
      aria-label={t("chat.exportAria")}
    >
      <Card className="border-border shadow-soft bg-card/95 backdrop-blur-md">
        <CardHeader className="space-y-1 pb-2 pr-10 relative">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1 h-8 w-8 rounded-full text-muted-foreground"
            onClick={onDismiss}
            aria-label={t("chat.exportDismiss")}
          >
            <X className="h-4 w-4" />
          </Button>
          <CardTitle className="text-sm font-display leading-tight">{t("chat.exportHeadline")}</CardTitle>
          <CardDescription className="text-xs leading-snug space-y-1.5">
            <span className="block">{t("chat.exportHint")}</span>
            <span className="block text-muted-foreground/95">{t("chat.exportPrivacy")}</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <Button type="button" size="sm" className="w-full gap-2 rounded-full bg-gradient-primary" onClick={handleDownload}>
            <Download className="h-4 w-4" />
            {t("chat.exportDownload")}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default ExportChatPrompt;
