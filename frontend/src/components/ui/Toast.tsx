import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface ToastMessage {
  id: number;
  text: string;
  tone: "success" | "error";
}

interface ToastContextValue {
  show: (text: string, tone?: ToastMessage["tone"]) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const show = useCallback((text: string, tone: ToastMessage["tone"] = "success") => {
    const id = Date.now();
    setMessages((prev) => [...prev, { id, text, tone }]);
    setTimeout(() => setMessages((prev) => prev.filter((m) => m.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" role="status" aria-live="polite">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-lg border px-4 py-2.5 text-sm font-medium shadow-panel ${
              m.tone === "success"
                ? "bg-teal text-white border-teal/60"
                : "bg-red-600 text-white border-red-700 dark:bg-red-700 dark:border-red-800"
            }`}
          >
            {m.text}
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
