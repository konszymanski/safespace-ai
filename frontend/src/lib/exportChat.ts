import type { ChatMessage } from "@/lib/mockApi";



/** Plain-text transcript for a local download (no server). */

export function buildChatExportText(

  messages: ChatMessage[],

  headerLines: string[],

  roleLabels: { user: string; assistant: string },

  footer: string,

): string {

  const parts: string[] = [...headerLines, "", "—", ""];

  for (const m of messages) {

    const label = m.role === "user" ? roleLabels.user : roleLabels.assistant;

    parts.push(`${label}: ${m.content}`);

    parts.push("");

  }

  parts.push("—", "", footer);

  return parts.join("\n").trimEnd() + "\n";

}



export function downloadTextFile(content: string, filename: string): void {

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });

  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");

  a.href = url;

  a.download = filename;

  a.rel = "noopener";

  document.body.appendChild(a);

  a.click();

  a.remove();

  URL.revokeObjectURL(url);

}



export function exportChatFilename(): string {

  const d = new Date();

  const y = d.getFullYear();

  const mo = String(d.getMonth() + 1).padStart(2, "0");

  const day = String(d.getDate()).padStart(2, "0");

  return `safe-space-chat-${y}-${mo}-${day}.txt`;

}

