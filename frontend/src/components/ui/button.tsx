"use client";

import { ExternalLink, LoaderCircle, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { safeUrl } from "@/lib/safe-url";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-control border text-label font-semibold " +
  "text-center transition-colors duration-[var(--duration-fast)] ease-standard select-none";

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-on-accent border-accent hover:bg-accent-hover hover:border-accent-hover active:bg-accent-active active:border-accent-active",
  secondary:
    "bg-surface text-ink border-line hover:bg-surface-hover active:bg-surface-raised active:border-accent",
  ghost:
    "bg-transparent text-ink-secondary border-transparent hover:bg-surface-hover hover:text-ink active:bg-surface-raised active:border-line",
  danger:
    "bg-danger text-on-danger border-danger hover:bg-danger-hover hover:border-danger-hover active:bg-danger-active active:border-danger-active",
};

const sizes: Record<ButtonSize, string> = {
  sm: "min-h-11 px-3 py-2",
  md: "min-h-12 px-4 py-2.5",
  lg: "min-h-14 px-6 py-3",
};

const disabledCls =
  "bg-surface-raised text-ink-muted border-line cursor-not-allowed hover:bg-surface-raised hover:text-ink-muted";

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
    <Link href={href} className={cn("text-accent underline underline-offset-[0.2em] hover:text-accent", className)}>
      {children}
    </Link>
  );
}
