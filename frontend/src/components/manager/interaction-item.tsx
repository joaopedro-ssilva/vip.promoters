import { MessageCircle, Smartphone } from "lucide-react";
import Link from "next/link";
import { StatusBadge, type BadgeKind } from "@/components/ui/badge";
import { PointsChip } from "@/components/ui/misc";
import type { Interaction } from "@/lib/api/types";
import { formatDateTime, formatSignedPoints } from "@/lib/format";

const KIND: Record<Interaction["status"], BadgeKind> = {
  awarded: "awarded",
  duplicate: "duplicate",
  unmatched: "unmatched",
  out_of_window: "out_of_window",
};

export function InteractionItem({ item, showCampaignLink }: { item: Interaction; showCampaignLink?: boolean }) {
  const isComment = item.type === "comment";
  const Icon = isComment ? MessageCircle : Smartphone;
  return (
    <li className="min-w-0 rounded-card border border-line-subtle bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="text-body font-bold">
            {item.promoter?.name ?? `@${item.ig_username}`}
            {item.promoter && <span className="ml-2 text-label font-normal text-ink-muted">@{item.ig_username}</span>}
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 text-caption text-ink-muted">
            <Icon aria-hidden="true" strokeWidth={1.75} className="size-4" />
            <span>{isComment ? "Comentário" : "Menção em story"}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={item.occurred_at} className="tabular-nums">
              {formatDateTime(item.occurred_at)}
            </time>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge kind={KIND[item.status]} />
          {item.status === "awarded" && item.points_awarded > 0 && <PointsChip>{formatSignedPoints(item.points_awarded)}</PointsChip>}
        </div>
      </div>
      <p className="mt-3 text-body text-ink-secondary">{isComment ? (item.text ? `“${item.text}”` : "Comentário sem texto") : "Menção em story"}</p>
      {item.status === "unmatched" && (
        <p className="mt-2 text-label text-info">
          Este @ ainda não está vinculado a um promoter aprovado.{" "}
          <Link href="/gestor/equipe" className="text-accent underline">
            Ver equipe
          </Link>
        </p>
      )}
      {item.status === "duplicate" && (
        <p className="mt-2 text-label text-warning">
          {isComment
            ? "Este comentário não gerou pontos. O promoter já pontuou com um comentário nesta campanha."
            : "O promoter já pontuou com uma menção em story nesta campanha."}
        </p>
      )}
      {item.status === "out_of_window" && (
        <p className="mt-2 text-label text-ink-muted">Registrado fora do período da campanha. Não gerou pontos.</p>
      )}
      {showCampaignLink && item.campaign_id && (
        <p className="mt-2 text-label">
          <Link href={`/gestor/campanhas/${item.campaign_id}`} className="text-accent underline">
            Ver campanha
          </Link>
        </p>
      )}
    </li>
  );
}
