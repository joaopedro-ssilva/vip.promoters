import { Medal, Trophy } from "lucide-react";
import { Avatar } from "@/components/ui/misc";
import { cn } from "@/lib/cn";
import { formatOrdinal, formatPoints } from "@/lib/format";
import type { LeaderboardEntry } from "@/lib/api/types";

export function RankingList({ entries, meMembershipId }: { entries: LeaderboardEntry[]; meMembershipId?: string | null }) {
  return (
    <ol className="overflow-hidden rounded-card border border-line-subtle">
      {entries.map((e) => {
        const me = meMembershipId != null && e.membership_id === meMembershipId;
        const top = e.rank <= 3;
        const posColor = e.rank === 1 ? "text-success" : e.rank === 2 ? "text-accent-secondary" : "text-info";
        return (
          <li
            key={e.membership_id}
            aria-current={me ? "true" : undefined}
            className={cn(
              "flex min-h-[4.5rem] flex-wrap items-center gap-x-3 gap-y-1 border-b border-line-subtle px-4 py-3 last:border-b-0",
              me ? "bg-surface-raised" : "bg-surface",
            )}
          >
            <span className={cn("w-10 shrink-0 font-sans text-page font-extrabold tracking-[-0.02em] tabular-nums", top ? posColor : "text-ink")}>
              <span className="sr-only">{formatOrdinal(e.rank)} lugar</span>
              <span aria-hidden="true">{e.rank}º</span>
            </span>
            {top && (
              <span aria-hidden="true">
                {e.rank === 1 ? (
                  <Trophy strokeWidth={1.75} className="size-5 text-success" />
                ) : (
                  <Medal strokeWidth={1.75} className={cn("size-5", posColor)} />
                )}
              </span>
            )}
            <Avatar name={e.name} size="md" />
            <div className="min-w-0 flex-1 basis-40">
              <p className="text-body font-bold">
                {e.name}
                {me && <span className="ml-2 text-label text-success">Você</span>}
              </p>
              <p className="text-caption text-ink-muted">@{e.instagram_username}</p>
            </div>
            <p className="ml-auto text-label tabular-nums text-ink">{formatPoints(e.points)}</p>
          </li>
        );
      })}
    </ol>
  );
}

export const PERIOD_OPTIONS = [
  { value: "30d", label: "Últimos 30 dias" },
  { value: "7d", label: "Últimos 7 dias" },
  { value: "all", label: "Todo o período" },
] as const;

export const TIEBREAK_TEXT =
  "Desempate: quem alcançou a pontuação primeiro fica à frente; se persistir, vale a ordem alfabética do nome. Trocar pontos por benefícios não reduz sua posição.";
