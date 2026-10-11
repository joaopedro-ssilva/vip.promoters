"use client";

import { createContext, useCallback, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

const CloseContext = createContext<() => void>(() => {});

/** Closes the surrounding Popover and returns focus to its trigger. */
export function usePopoverClose() {
  return useContext(CloseContext);
}

interface PopoverProps {
  /** accessible name of the trigger button */
  label: string;
  trigger: ReactNode;
  children: ReactNode;
  align?: "left" | "right";
  panelClassName?: string;
  triggerClassName?: string;
}

/** Lightweight popover: outside click / Escape close it and focus returns to the trigger. */
export function Popover({ label, trigger, children, align = "right", panelClassName, triggerClassName }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  const close = useCallback(() => {
    setOpen(false);
    btnRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={wrapRef} className="relative">
      <button
        ref={btnRef}
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "relative grid min-h-11 min-w-11 place-items-center rounded-control border border-transparent text-ink-secondary hover:bg-surface-hover hover:text-ink active:bg-surface-raised",
          triggerClassName,
        )}
      >
        {trigger}
      </button>
      {open && (
        <div
          id={panelId}
          className={cn(
            "fixed inset-x-4 top-[calc(var(--topbar-height)+0.5rem)] z-40 rounded-card border border-line bg-surface p-2 text-ink shadow-popover animate-enter",
            "sm:absolute sm:inset-x-auto sm:top-full sm:mt-2 sm:w-[22rem]",
            align === "right" ? "sm:right-0" : "sm:left-0",
            panelClassName,
          )}
        >
          <CloseContext.Provider value={close}>{children}</CloseContext.Provider>
        </div>
      )}
    </div>
  );
}
