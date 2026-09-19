import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

import { XIcon } from "./icons";

interface ToastMessage {
  id: number;
  text: string;
  tone: "success" | "error" | "info";
}

interface ToastContextValue {
  show: (text: string, tone?: ToastMessage["tone"]) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TONE_CLASSES: Record<ToastMessage["tone"], string> = {
  success: "bg-teal text-white border-teal/60",
  error: "bg-red-600 text-white border-red-700 dark:bg-red-700 dark:border-red-800",
  info: "bg-surface text-ink border-border",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const show = useCallback((text: string, tone: ToastMessage["tone"] = "success") => {
    const id = Date.now();
    setMessages((prev) => [...prev, { id, text, tone }]);
    setTimeout(() => setMessages((prev) => prev.filter((m) => m.id !== id)), 4000);
  }, []);

  const dismiss = (id: number) => setMessages((prev) => prev.filter((m) => m.id !== id));

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" role="status" aria-live="polite">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-center gap-3 rounded-lg border py-2.5 pl-4 pr-2 text-sm font-medium shadow-panel ${TONE_CLASSES[m.tone]}`}
          >
            <span>{m.text}</span>
            <button
              type="button"
              aria-label="Dismiss"
              className="rounded p-0.5 opacity-80 transition-opacity hover:opacity-100"
              onClick={() => dismiss(m.id)}
            >
              <XIcon className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
