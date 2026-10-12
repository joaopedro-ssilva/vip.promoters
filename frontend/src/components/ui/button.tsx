"use client";

import { ExternalLink, LoaderCircle, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { safeUrl } from "@/lib/safe-url";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

// Variantes do design system (Camarim, "Componentes"):
// - primary: GEL LIMA. A ação principal — uma por tela, sempre.
// - secondary: VIDRO FINO. Toda outra ação com moldura.
// - ghost: só texto, ganha um véu no hover. Ação terciária.
// - danger: rosa suave em repouso e preenchimento cheio no hover.
const base =
  "inline-flex items-center justify-center gap-2 rounded-control text-label font-semibold tracking-[-0.005em] " +
  "text-center select-none transition-[background-color,border-color,color,filter,transform,box-shadow] " +
  "duration-[var(--duration-fast)] ease-standard active:scale-[0.985]";

const variants: Record<ButtonVariant, string> = {
  primary: "gel-lima",
  secondary: "vidro-fino text-ink hover:text-ink-strong",
  ghost:
    "bg-transparent text-ink-secondary border border-transparent hover:bg-[var(--hover-veu)] hover:text-ink-strong",
  danger:
    "bg-danger-soft text-danger border border-danger-border hover:bg-danger-active hover:border-danger-active hover:text-on-danger",
};

const sizes: Record<ButtonSize, string> = {
  sm: "min-h-11 px-3.5 py-2",
  md: "min-h-11 px-5 py-2.5",
  lg: "min-h-13 px-6 py-3 text-body",
};

const disabledCls =
  "border border-line-subtle bg-surface-raised text-ink-muted opacity-60 cursor-not-allowed active:scale-100";

export function buttonClasses(opts: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  disabled?: boolean;
  iconOnly?: boolean;
  className?: string;
}) {
  const { variant = "primary", size = "md", block, disabled, iconOnly, className } = opts;
  return cn(
    base,
    sizes[size],
    iconOnly && "min-w-11 px-0",
    disabled ? disabledCls : variants[variant],
    block && "w-full",
    className,
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  loading?: boolean;
  icon?: LucideIcon;
  /** icon-only button: `aria-label` is required */
  iconOnly?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  block,
  loading,
  icon: Icon,
  iconOnly,
  className,
  children,
  disabled,
  type = "button",
  onClick,
  ...rest
}: ButtonProps) {
  const Glyph = loading ? LoaderCircle : Icon;
  return (
    <button
      type={type}
      disabled={disabled}
      aria-busy={loading || undefined}
      aria-disabled={loading || undefined}
      onClick={(e) => {
        if (loading) {
          e.preventDefault();
          return;
        }
        onClick?.(e);
      }}
      className={buttonClasses({ variant, size, block, disabled, iconOnly, className })}
      {...rest}
    >
      {Glyph && (
        <Glyph
          aria-hidden="true"
          strokeWidth={1.75}
          className={cn(iconOnly ? "size-5" : "size-4 shrink-0", loading && "animate-spinner")}
        />
      )}
      {!iconOnly && <span className="min-w-0">{children}</span>}
      {iconOnly && !Glyph && children}
    </button>
  );
}

interface ButtonLinkProps {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  icon?: LucideIcon;
  /** external https link opened in a new tab */
  external?: boolean;
  className?: string;
  children: ReactNode;
  prefetch?: boolean;
}

export function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  block,
  icon: Icon,
  external,
  className,
  children,
  prefetch,
}: ButtonLinkProps) {
  const cls = buttonClasses({ variant, size, block, className });
  if (external) {
    const safe = safeUrl(href);
    if (!safe) return null;
    return (
      <a href={safe} target="_blank" rel="noopener noreferrer" className={cls}>
        {Icon && <Icon aria-hidden="true" strokeWidth={1.75} className="size-4 shrink-0" />}
        <span className="min-w-0">{children}</span>
        <ExternalLink aria-hidden="true" strokeWidth={1.75} className="size-4 shrink-0" />
        <span className="sr-only">(abre em nova aba)</span>
      </a>
    );
  }
  return (
    <Link href={href} prefetch={prefetch} className={cls}>
      {Icon && <Icon aria-hidden="true" strokeWidth={1.75} className="size-4 shrink-0" />}
      <span className="min-w-0">{children}</span>
    </Link>
  );
}

/** Persistent-underline text link in the accent colour. */
export function TextLink({
  href,
  children,
  className,
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link href={href} className={cn("font-semibold text-success underline underline-offset-[0.2em] hover:brightness-110", className)}>
      {children}
    </Link>
  );
}
