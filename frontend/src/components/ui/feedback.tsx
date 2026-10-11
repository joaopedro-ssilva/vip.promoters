import { CircleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Button } from "./button";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-skeleton rounded-control bg-surface-raised", className)} />;
}

export function SkeletonText({ lines = 2, className }: { lines?: number; className?: string }) {
  return (
    <div aria-hidden="true" className={cn("flex flex-col gap-3", className)}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={cn("h-3", i % 2 === 0 ? "w-3/4" : "w-1/2")} />
      ))}
    </div>
  );
}

/** One aria-busy region with a single "Carregando…" message for assistive tech. */
export function LoadingRegion({ children, className, label = "Carregando…" }: { children: ReactNode; className?: string; label?: string }) {
  return (
    <div role="status" aria-busy="true" className={className}>
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  align = "center",
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  align?: "center" | "start";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 px-4 py-8",
        align === "center" ? "items-center text-center" : "items-start text-left",
        className,
      )}
    >
      {Icon && <Icon aria-hidden="true" strokeWidth={1.75} className="size-8 text-ink-muted" />}
      <h3 className="font-heading text-section">{title}</h3>
      {description && <p className="max-w-[40ch] text-body text-ink-secondary">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({
  onRetry,
  message = "Não foi possível atualizar agora. Seus dados foram mantidos.",
  retrying,
  className,
}: {
  onRetry?: () => void;
  message?: string;
  retrying?: boolean;
  className?: string;
}) {
  return (
    <EmptyState
      icon={CircleAlert}
      title="Não foi possível carregar"
      description={message}
      className={className}
      action={
        onRetry && (
          <Button variant="secondary" onClick={onRetry} loading={retrying}>
            {retrying ? "Tentando…" : "Tentar novamente"}
          </Button>
        )
      }
    />
  );
}
