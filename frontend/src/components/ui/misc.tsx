"use client";

import { Check, Copy, Ticket, type LucideIcon } from "lucide-react";
import {
  useCallback,
  useId,
  useRef,
  useState,
  type HTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { cn } from "@/lib/cn";
import { formatNumber, initials } from "@/lib/format";
import { safeUrl } from "@/lib/safe-url";
import { Button } from "./button";
import { Skeleton } from "./feedback";
import { useToast } from "./toast";

/* ---------- Card ---------- */

export function Card({
  className,
  children,
  as: Tag = "div",
  ...rest
}: HTMLAttributes<HTMLElement> & { as?: "div" | "section" | "article" | "li" }) {
  return (
    <Tag className={cn("solido rounded-card p-4 shadow-card md:p-6", className)} {...rest}>
      {children}
    </Tag>
  );
}

/** Dense card for lists and rewards (16px padding). */
export function DenseCard({ className, children, as: Tag = "div", ...rest }: HTMLAttributes<HTMLElement> & { as?: "div" | "article" | "li" }) {
  return (
    <Tag className={cn("solido min-w-0 rounded-card p-4", className)} {...rest}>
      {children}
    </Tag>
  );
}

export function Perforated({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("border-t border-dashed border-line", className)} />;
}

/* ---------- Page header ---------- */

export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="min-w-0">
        <h1 tabIndex={-1} className="display text-page font-bold text-ink-strong outline-none">
          {title}
        </h1>
        {description && <p className="mt-1.5 max-w-[60ch] text-label font-normal text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3 sm:shrink-0">{actions}</div>}
    </div>
  );
}

export function SectionTitle({ children, id, className }: { children: ReactNode; id?: string; className?: string }) {
  return (
    <h2 id={id} className={cn("text-section font-semibold text-ink-strong", className)}>
      {children}
    </h2>
  );
}

/* ---------- Avatar ---------- */

const avatarSizes = { sm: "size-8 text-caption", md: "size-10 text-label", lg: "size-12 text-body" } as const;

export function Avatar({
  name,
  src,
  size = "md",
  className,
}: {
  name: string | null | undefined;
  src?: string | null;
  size?: keyof typeof avatarSizes;
  className?: string;
}) {
  const safe = safeUrl(src);
  const [failed, setFailed] = useState<string | null>(null);
  const showImg = safe && failed !== safe;
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative inline-grid shrink-0 place-items-center overflow-hidden rounded-pill border border-violet-border bg-violet-soft font-bold tracking-[0.02em] text-violet",
        avatarSizes[size],
        className,
      )}
    >
      {initials(name)}
      {showImg && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={safe}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setFailed(safe)}
          className="absolute inset-0 size-full bg-surface-raised object-cover"
        />
      )}
    </span>
  );
}

/* ---------- KPI ---------- */

export function Kpi({
  label,
  value,
  help,
  icon: Icon,
  loading,
}: {
  label: string;
  value: number | string | null | undefined;
  help?: string;
  icon?: LucideIcon;
  loading?: boolean;
}) {
  return (
    <div className="vidro flex min-w-0 flex-col gap-3 rounded-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="rotulo min-w-0">{label}</p>
        {Icon && <Icon aria-hidden="true" strokeWidth={1.75} className="size-4.5 shrink-0 text-ink-muted" />}
      </div>
      {loading ? (
        <Skeleton className="h-9 w-20" />
      ) : (
        <p className="cifra text-page text-ink-strong">
          {value === null || value === undefined ? "—" : typeof value === "number" ? formatNumber(value) : value}
        </p>
      )}
      {help && <p className="text-caption text-ink-muted">{help}</p>}
    </div>
  );
}

/* ---------- Points chip ---------- */

export function PointsChip({ children, muted, className }: { children: ReactNode; muted?: boolean; className?: string }) {
  return (
    <span
      className={cn(
        "num inline-flex min-h-7 items-center gap-1 rounded-pill border px-2.5 py-1 text-label",
        muted ? "border-line-subtle bg-surface-raised text-ink-secondary" : "border-accent-border bg-accent-soft text-success",
        className,
      )}
    >
      <Ticket aria-hidden="true" strokeWidth={1.75} className="size-4 shrink-0" />
      {children}
    </span>
  );
}

/* ---------- Copy ---------- */

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.className = "fixed -top-96 opacity-0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }
}

export function CopyButton({
  text,
  label,
  successMessage,
  variant = "ghost",
  size = "sm",
  iconOnly,
  className,
}: {
  text: string;
  label: string;
  successMessage: string;
  variant?: "ghost" | "secondary";
  size?: "sm" | "md";
  iconOnly?: boolean;
  className?: string;
}) {
  const toast = useToast();
  const [done, setDone] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const onClick = useCallback(async () => {
    const ok = await copyText(text);
    if (ok) {
      toast.success(successMessage);
      setDone(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setDone(false), 2000);
    } else {
      toast.error("Não foi possível copiar. Selecione o texto e copie manualmente.");
    }
  }, [text, successMessage, toast]);
  return (
    <Button
      variant={variant}
      size={size}
      iconOnly={iconOnly}
      icon={done ? Check : Copy}
      onClick={onClick}
      aria-label={iconOnly ? label : undefined}
      className={className}
    >
      {label}
    </Button>
  );
}

/* ---------- Filter buttons (aria-pressed, not tabs) ---------- */

export function FilterButtons<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="vidro-fino inline-flex w-fit max-w-full flex-wrap gap-1 rounded-control p-1">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "min-h-10 rounded-[0.5625rem] px-4 text-label transition-colors duration-[var(--duration-fast)]",
              active
                ? "segmento-ativo text-ink-strong"
                : "text-ink-muted hover:text-ink",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/* ---------- Tabs (real tablist) ---------- */

export function Tabs<T extends string>({
  label,
  tabs,
  value,
  onChange,
  children,
}: {
  label: string;
  tabs: { id: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  children: ReactNode;
}) {
  const base = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const move = (i: number) => {
    const next = tabs[(i + tabs.length) % tabs.length];
    refs.current[next.id]?.focus();
  };
  const onKey = (e: KeyboardEvent, i: number) => {
    const target =
      e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : null;
    if (target !== null) {
      e.preventDefault();
      move(target);
    }
  };
  return (
    <div>
      <div role="tablist" aria-label={label} className="flex flex-wrap border-b border-line-subtle">
        {tabs.map((t, i) => {
          const selected = t.id === value;
          return (
            <button
              key={t.id}
              ref={(el) => {
                refs.current[t.id] = el;
              }}
              role="tab"
              type="button"
              id={`${base}-tab-${t.id}`}
              aria-selected={selected}
              aria-controls={`${base}-panel`}
              tabIndex={selected ? 0 : -1}
              onKeyDown={(e) => onKey(e, i)}
              onClick={() => onChange(t.id)}
              className={cn(
                "-mb-px min-h-12 border-b-2 px-4 py-3 text-label transition-colors duration-[var(--duration-fast)]",
                selected
                  ? "border-accent text-ink-strong"
                  : "border-transparent text-ink-muted hover:text-ink",
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-tab-${value}`} className="pt-6">
        {children}
      </div>
    </div>
  );
}

/* ---------- Pagination ---------- */

export function Pagination({
  total,
  limit,
  offset,
  onChange,
  busy,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
  busy?: boolean;
}) {
  if (total <= limit) return null;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <nav aria-label="Paginação" className="mt-6 flex flex-wrap items-center justify-between gap-3">
      <p className="num text-label font-normal text-ink-muted" aria-live="polite">
        {busy ? "Atualizando…" : `${formatNumber(from)}–${formatNumber(to)} de ${formatNumber(total)}`}
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" disabled={offset <= 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Anterior
        </Button>
        <Button variant="secondary" size="sm" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
          Próxima
        </Button>
      </div>
    </nav>
  );
}

/* ---------- Dialog footer used inside <form> ---------- */

export function DialogActions({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:justify-end [&>*]:w-full sm:[&>*]:w-auto">{children}</div>;
}

/* ---------- Definition pair ---------- */

export function Pair({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("min-w-0", className)}>
      <dt className="rotulo">{label}</dt>
      <dd className="num mt-0.5 text-label font-medium text-ink">{children}</dd>
    </div>
  );
}
