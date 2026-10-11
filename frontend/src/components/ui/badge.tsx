import {
  BadgeCheck,
  CircleCheck,
  CircleX,
  Clock3,
  Copy,
  FilePenLine,
  Flag,
  PackageCheck,
  Radio,
  UserRoundSearch,
  UserRoundX,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";

export type BadgeKind =
  | "pending"
  | "approved"
  | "active"
  | "ended"
  | "draft"
  | "awarded"
  | "duplicate"
  | "unmatched"
  | "fulfilled"
  | "cancelled"
  | "rejected"
  | "removed"
  | "out_of_window"
  | "sold_out";

const MAP: Record<BadgeKind, { label: string; campaignLabel?: string; color: string; Icon: LucideIcon }> = {
  pending: { label: "Pendente", color: "text-warning", Icon: Clock3 },
  approved: { label: "Aprovado", color: "text-success", Icon: CircleCheck },
  active: { label: "Ativo", campaignLabel: "Ativa", color: "text-accent", Icon: Radio },
  ended: { label: "Encerrado", campaignLabel: "Encerrada", color: "text-ink-secondary", Icon: Flag },
  draft: { label: "Rascunho", color: "text-ink-muted", Icon: FilePenLine },
  awarded: { label: "Pontuou", color: "text-success", Icon: BadgeCheck },
  duplicate: { label: "Duplicado", color: "text-warning", Icon: Copy },
  unmatched: { label: "Não identificado", color: "text-info", Icon: UserRoundSearch },
  fulfilled: { label: "Cumprido", color: "text-success", Icon: PackageCheck },
  cancelled: { label: "Cancelado", color: "text-danger", Icon: CircleX },
  rejected: { label: "Recusado", color: "text-danger", Icon: UserRoundX },
  removed: { label: "Removido", color: "text-ink-secondary", Icon: UserRoundX },
  out_of_window: { label: "Fora do período", color: "text-ink-muted", Icon: Clock3 },
  sold_out: { label: "Esgotado", color: "text-ink-secondary", Icon: Flag },
};

export function StatusBadge({
  kind,
  campaign,
  className,
}: {
  kind: BadgeKind;
  /** use "Ativa"/"Encerrada" wording */
  campaign?: boolean;
  className?: string;
}) {
  const { label, campaignLabel, color, Icon } = MAP[kind];
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1 rounded-pill border border-line bg-surface-raised px-2 py-1 text-caption",
        color,
        className,
      )}
    >
      <Icon aria-hidden="true" strokeWidth={1.75} className="size-4 shrink-0" />
      {campaign && campaignLabel ? campaignLabel : label}
    </span>
  );
}
