"use client";

import { ChevronDown, CircleAlert, Eye, EyeOff } from "lucide-react";
import {
  useId,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { cn } from "@/lib/cn";

const controlBase =
  "block w-full rounded-control border border-line bg-surface-sunken px-3.5 py-3 text-base text-ink-strong " +
  "transition-[border-color,box-shadow] duration-[var(--duration-fast)] " +
  "hover:border-ink-muted focus-visible:border-accent-border focus-visible:shadow-[0_0_0_3px_var(--accent-soft)] " +
  "focus-visible:outline-none aria-[invalid=true]:border-danger-border " +
  "disabled:cursor-not-allowed disabled:bg-surface-raised disabled:text-ink-muted " +
  "read-only:bg-surface-sunken";

interface ShellProps {
  id: string;
  label: ReactNode;
  optional?: boolean;
  hint?: ReactNode;
  error?: string;
  className?: string;
  children: ReactNode;
  hideLabel?: boolean;
}

function FieldShell({ id, label, optional, hint, error, className, children, hideLabel }: ShellProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <label
        htmlFor={id}
        className={cn("rotulo mb-2 block", hideLabel && "sr-only")}
      >
        {label}
        {optional && <span className="font-medium normal-case tracking-normal text-ink-muted"> (opcional)</span>}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1 text-caption text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1 flex items-start gap-1 text-label text-danger">
          <CircleAlert aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0" />
          <span className="min-w-0">{error}</span>
        </p>
      )}
    </div>
  );
}

function describedBy(id: string, hint?: ReactNode, error?: string) {
  if (error) return `${id}-error`;
  if (hint) return `${id}-hint`;
  return undefined;
}

type FieldCommon = {
  label: ReactNode;
  optional?: boolean;
  hint?: ReactNode;
  error?: string;
  hideLabel?: boolean;
};

export function TextField({
  label,
  optional,
  hint,
  error,
  hideLabel,
  className,
  id: idProp,
  ...rest
}: FieldCommon & InputHTMLAttributes<HTMLInputElement>) {
  const auto = useId();
  const id = idProp ?? auto;
  return (
    <FieldShell id={id} label={label} optional={optional} hint={hint} error={error} className={className} hideLabel={hideLabel}>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        className={cn(controlBase, "min-h-12")}
        {...rest}
      />
    </FieldShell>
  );
}

export function PasswordField({
  label,
  optional,
  hint,
  error,
  className,
  id: idProp,
  ...rest
}: FieldCommon & Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  const auto = useId();
  const id = idProp ?? auto;
  const [shown, setShown] = useState(false);
  return (
    <FieldShell id={id} label={label} optional={optional} hint={hint} error={error} className={className}>
      <div className="relative">
        <input
          id={id}
          type={shown ? "text" : "password"}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, hint, error)}
          className={cn(controlBase, "min-h-12 pr-14")}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setShown((s) => !s)}
          aria-label={shown ? "Ocultar senha" : "Mostrar senha"}
          aria-pressed={shown}
          className="absolute right-0 top-0 grid size-12 place-items-center rounded-control text-ink-secondary hover:text-ink"
        >
          {shown ? (
            <EyeOff aria-hidden="true" strokeWidth={1.75} className="size-5" />
          ) : (
            <Eye aria-hidden="true" strokeWidth={1.75} className="size-5" />
          )}
        </button>
      </div>
    </FieldShell>
  );
}

export function TextareaField({
  label,
  optional,
  hint,
  error,
  className,
  id: idProp,
  ...rest
}: FieldCommon & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const auto = useId();
  const id = idProp ?? auto;
  return (
    <FieldShell id={id} label={label} optional={optional} hint={hint} error={error} className={className}>
      <textarea
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        className={cn(controlBase, "min-h-32 resize-y")}
        {...rest}
      />
    </FieldShell>
  );
}

export function SelectField({
  label,
  optional,
  hint,
  error,
  hideLabel,
  className,
  id: idProp,
  children,
  ...rest
}: FieldCommon & SelectHTMLAttributes<HTMLSelectElement>) {
  const auto = useId();
  const id = idProp ?? auto;
  return (
    <FieldShell id={id} label={label} optional={optional} hint={hint} error={error} className={className} hideLabel={hideLabel}>
      <div className="relative">
        <select
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, hint, error)}
          className={cn(controlBase, "min-h-12 appearance-none pr-10")}
          {...rest}
        >
          {children}
        </select>
        <ChevronDown
          aria-hidden="true"
          strokeWidth={1.75}
          className="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-ink-secondary"
        />
      </div>
    </FieldShell>
  );
}

export function CheckboxField({
  label,
  hint,
  className,
  id: idProp,
  ...rest
}: { label: ReactNode; hint?: ReactNode } & Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  const auto = useId();
  const id = idProp ?? auto;
  return (
    <div className={cn("min-w-0", className)}>
      <label htmlFor={id} className="flex min-h-11 cursor-pointer items-center gap-3 text-label text-ink">
        <input
          id={id}
          type="checkbox"
          aria-describedby={hint ? `${id}-hint` : undefined}
          className="size-5 shrink-0 cursor-pointer rounded-[4px]"
          {...rest}
        />
        <span className="min-w-0">{label}</span>
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-caption text-ink-muted">
          {hint}
        </p>
      )}
    </div>
  );
}

export function FormError({ message, id }: { message: string | null | undefined; id?: string }) {
  if (!message) return null;
  return (
    <div
      id={id}
      role="alert"
      className="flex items-start gap-2 rounded-control border border-danger-border bg-danger-soft p-3 text-label text-danger"
    >
      <CircleAlert aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0" />
      <span className="min-w-0">{message}</span>
    </div>
  );
}
