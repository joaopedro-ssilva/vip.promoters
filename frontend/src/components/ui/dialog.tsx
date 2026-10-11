"use client";

import { X } from "lucide-react";
import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Button, type ButtonVariant } from "./button";
import { FormError } from "./fields";

const DirtyContext = createContext<((dirty: boolean) => void) | null>(null);

/** Forms inside a <Dialog> report their dirty state so closing asks "Descartar alterações?". */
export function useDialogDirty(dirty: boolean) {
  const set = useContext(DirtyContext);
  useEffect(() => {
    set?.(dirty);
    return () => set?.(false);
  }, [dirty, set]);
}

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  size?: "sm" | "lg";
  /** when true, closing asks "Descartar alterações?" first */
  dirty?: boolean;
  /** backdrop click closes (informative dialogs without data only) */
  dismissOnBackdrop?: boolean;
  children?: ReactNode;
  footer?: ReactNode;
}

/**
 * Native modal <dialog>: focus trap, inert background, Escape and focus return
 * are provided by the platform. Children are only mounted while open so forms
 * start fresh on every opening. Mark the element that should receive the
 * initial focus with `data-autofocus`.
 */
export function Dialog({
  open,
  onClose,
  title,
  description,
  size = "sm",
  dirty,
  dismissOnBackdrop,
  children,
  footer,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      d.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    } else if (!open && d.open) {
      d.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onCancel={(e) => {
        e.preventDefault();
        // Escape handled by the body (it may need to confirm discarding)
        ref.current?.dispatchEvent(new CustomEvent("vip:request-close"));
      }}
      onClick={(e) => {
        if (dismissOnBackdrop && e.target === e.currentTarget) onClose();
      }}
      className={cn(
        "m-auto max-h-[calc(100dvh-2rem)] overflow-y-auto rounded-panel border border-line bg-surface p-0 text-ink shadow-dialog",
        "backdrop:bg-[var(--scrim)] open:animate-enter",
        size === "sm" ? "w-[min(30rem,calc(100%-2rem))]" : "w-[min(48rem,calc(100%-2rem))]",
      )}
    >
      {open && (
        <DialogBody
          dialogRef={ref}
          titleId={titleId}
          descId={descId}
          title={title}
          description={description}
          dirty={dirty}
          onClose={onClose}
          footer={footer}
        >
          {children}
        </DialogBody>
      )}
    </dialog>
  );
}

function DialogBody({
  dialogRef,
  titleId,
  descId,
  title,
  description,
  dirty,
  onClose,
  footer,
  children,
}: {
  dialogRef: React.RefObject<HTMLDialogElement | null>;
  titleId: string;
  descId: string;
  title: string;
  description?: ReactNode;
  dirty?: boolean;
  onClose: () => void;
  footer?: ReactNode;
  children?: ReactNode;
}) {
  const [confirming, setConfirming] = useState(false);
  const dirtyRef = useRef(dirty);
  const [reported, setReported] = useState(false);
  const confirmingRef = useRef(confirming);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    dirtyRef.current = dirty || reported;
    confirmingRef.current = confirming;
    onCloseRef.current = onClose;
  });

  const requestClose = () => {
    if (dirtyRef.current && !confirmingRef.current) setConfirming(true);
    else onCloseRef.current();
  };

  useEffect(() => {
    const d = dialogRef.current;
    if (!d) return;
    const handler = () => requestClose();
    d.addEventListener("vip:request-close", handler);
    return () => d.removeEventListener("vip:request-close", handler);
  }, [dialogRef]);

  return (
    <DirtyContext.Provider value={setReported}>
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <div className="flex items-start justify-between gap-3">
        <h2 id={titleId} className="min-w-0 font-heading text-section">
          {title}
        </h2>
        <Button variant="ghost" iconOnly aria-label="Fechar" onClick={requestClose} className="-mr-2 -mt-1 shrink-0">
          <X aria-hidden="true" strokeWidth={1.75} className="size-5" />
        </Button>
      </div>
      {description && (
        <div id={descId} className="text-body text-ink-secondary">
          {description}
        </div>
      )}
      {confirming && (
        <div role="alert" className="flex flex-col gap-3 rounded-control border border-warning bg-surface-raised p-3">
          <p className="text-label text-warning">Descartar alterações? O que você preencheu será perdido.</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => setConfirming(false)} data-autofocus>
              Continuar editando
            </Button>
            <Button size="sm" variant="danger" onClick={() => onCloseRef.current()}>
              Descartar
            </Button>
          </div>
        </div>
      )}
      {children}
      {footer && (
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-end [&>*]:w-full sm:[&>*]:w-auto">
          {footer}
        </div>
      )}
    </div>
    </DirtyContext.Provider>
  );
}

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: ReactNode;
  confirmLabel: string;
  loadingLabel?: string;
  cancelLabel?: string;
  variant?: ButtonVariant;
  loading?: boolean;
  error?: string | null;
  children?: ReactNode;
}

/** Confirmation dialog; destructive confirmations start with focus on "Voltar". */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  loadingLabel,
  cancelLabel = "Voltar",
  variant = "primary",
  loading,
  error,
  children,
}: ConfirmDialogProps) {
  const destructive = variant === "danger";
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} data-autofocus={destructive ? "" : undefined}>
            {cancelLabel}
          </Button>
          <Button
            variant={variant}
            loading={loading}
            onClick={onConfirm}
            data-autofocus={destructive ? undefined : ""}
          >
            {loading && loadingLabel ? loadingLabel : confirmLabel}
          </Button>
        </>
      }
    >
      {children}
      <FormError message={error} />
    </Dialog>
  );
}
