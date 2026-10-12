"use client";

import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "@/lib/cn";
import { Button } from "./button";

type Tone = "success" | "info" | "warning" | "danger";

interface ToastInput {
  title: string;
  description?: string;
  tone?: Tone;
}

interface ToastItem extends Required<Pick<ToastInput, "title" | "tone">> {
  id: number;
  description?: string;
}

interface ToastApi {
  toast: (t: ToastInput) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const toneStyles: Record<Tone, { border: string; text: string; Icon: typeof Info }> = {
  success: { border: "border-l-success", text: "text-success", Icon: CircleCheck },
  info: { border: "border-l-info", text: "text-info", Icon: Info },
  warning: { border: "border-l-warning", text: "text-warning", Icon: TriangleAlert },
  danger: { border: "border-l-danger", text: "text-danger", Icon: CircleAlert },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: number) => {
    setItems((list) => list.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((t: ToastInput) => {
    const id = ++counter.current;
    setItems((list) => [...list.slice(-2), { id, title: t.title, description: t.description, tone: t.tone ?? "info" }]);
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      toast: push,
      success: (title, description) => push({ title, description, tone: "success" }),
      error: (title, description) => push({ title, description, tone: "danger" }),
      info: (title, description) => push({ title, description, tone: "info" }),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-region pointer-events-none fixed z-70 flex flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <ToastView key={t.id} item={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastView({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const [paused, setPaused] = useState(false);
  const persistent = item.tone === "danger" || item.tone === "warning";
  useEffect(() => {
    if (persistent || paused) return;
    const timer = window.setTimeout(onDismiss, 6000);
    return () => window.clearTimeout(timer);
  }, [persistent, paused, onDismiss]);

  const { border, text, Icon } = toneStyles[item.tone];
  return (
    <div
      role={item.tone === "danger" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className={cn(
        "pointer-events-auto flex w-[min(24rem,calc(100vw-2rem))] items-start gap-3 rounded-[1rem] border border-l-[3px] border-line-subtle bg-surface-raised p-4 text-ink shadow-popover animate-enter",
        border,
      )}
    >
      <Icon aria-hidden="true" strokeWidth={1.75} className={cn("mt-0.5 size-5 shrink-0", text)} />
      <div className="min-w-0 flex-1">
        <p className="text-label">{item.title}</p>
        {item.description && <p className="mt-1 text-label font-normal text-ink-secondary">{item.description}</p>}
      </div>
      <Button variant="ghost" iconOnly aria-label="Fechar aviso" onClick={onDismiss} className="-m-2 shrink-0">
        <X aria-hidden="true" strokeWidth={1.75} className="size-5" />
      </Button>
    </div>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
