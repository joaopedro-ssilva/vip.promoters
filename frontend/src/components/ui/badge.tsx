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

// Tons do design system: lima = já valeu (pontuou, aprovado, cumprido);
// violeta = ainda em jogo (campanha ativa, não identificado); âmbar = atenção
// (pendente, duplicado); rosa = recusa e cancelamento; o resto fica neutro.
const TONE = {
  lima: "bg-accent-soft border-accent-border text-success",
  violeta: "bg-violet-soft border-violet-border text-violet",
  ambar: "bg-warning-soft border-warning-border text-warning",
  rosa: "bg-danger-soft border-danger-border text-danger",
  neutro: "bg-surface-raised border-line-subtle text-ink-secondary",
  apagado: "bg-surface-raised border-line-subtle text-ink-muted",
} as const;

const MAP: Record<BadgeKind, { label: string; campaignLabel?: string; color: string; Icon: LucideIcon }> = {
  pending: { label: "Pendente", color: TONE.ambar, Icon: Clock3 },
  approved: { label: "Aprovado", color: TONE.lima, Icon: CircleCheck },
  active: { label: "Ativo", campaignLabel: "Ativa", color: TONE.violeta, Icon: Radio },
  ended: { label: "Encerrado", campaignLabel: "Encerrada", color: TONE.neutro, Icon: Flag },
  draft: { label: "Rascunho", color: TONE.apagado, Icon: FilePenLine },
  awarded: { label: "Pontuou", color: TONE.lima, Icon: BadgeCheck },
  duplicate: { label: "Duplicado", color: TONE.ambar, Icon: Copy },
  unmatched: { label: "Não identificado", color: TONE.violeta, Icon: UserRoundSearch },
  fulfilled: { label: "Cumprido", color: TONE.lima, Icon: PackageCheck },
  cancelled: { label: "Cancelado", color: TONE.rosa, Icon: CircleX },
  rejected: { label: "Recusado", color: TONE.rosa, Icon: UserRoundX },
  removed: { label: "Removido", color: TONE.neutro, Icon: UserRoundX },
  out_of_window: { label: "Fora do período", color: TONE.apagado, Icon: Clock3 },
  sold_out: { label: "Esgotado", color: TONE.neutro, Icon: Flag },
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
        "inline-flex min-h-6 items-center gap-1.5 whitespace-nowrap rounded-pill border px-2.5 py-0.5 text-2xs font-semibold tracking-[0.04em]",
        color,
        className,
      )}
    >
      <Icon aria-hidden="true" strokeWidth={2} className="size-3.5 shrink-0" />
      {campaign && campaignLabel ? campaignLabel : label}
    </span>
  );
}
