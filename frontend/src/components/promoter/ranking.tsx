"use client";

import { useQuery } from "@tanstack/react-query";
import { Trophy } from "lucide-react";
import { useState } from "react";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { SelectField } from "@/components/ui/fields";
import { Card, PageHeader } from "@/components/ui/misc";
import { PERIOD_OPTIONS, RankingList, TIEBREAK_TEXT } from "@/components/shared/ranking-list";
import { promoterApi } from "@/lib/api/promoter";
import type { LeaderboardPeriod } from "@/lib/api/types";
import { formatOrdinal, formatPoints } from "@/lib/format";
import { keys } from "@/lib/queries";
import { TeamGate } from "./team-provider";

export function PromoterRanking() {
  return (
    <>
      <PageHeader title="Ranking" description="Pontos ganhos no período. Trocar pontos por benefícios não reduz sua posição." />
      <TeamGate>{(orgId) => <Body orgId={orgId} />}</TeamGate>
    </>
  );
}

function Body({ orgId }: { orgId: string }) {
  const [period, setPeriod] = useState<LeaderboardPeriod>("30d");
  const q = useQuery({
    queryKey: [...keys.promoter(orgId), "leaderboard", period],
    queryFn: () => promoterApi.leaderboard(orgId, period),
  });
  const meEntry = q.data?.items.find((e) => q.data?.me?.rank === e.rank);
  return (
    <div className="mx-auto max-w-reading">
      <SelectField label="Período" value={period} onChange={(e) => setPeriod(e.target.value as LeaderboardPeriod)} className="mb-6 max-w-xs">
        {PERIOD_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </SelectField>
      {q.isPending ? (
        <LoadingRegion className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-[4.5rem]" />
          ))}
        </LoadingRegion>
      ) : q.isError ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : (
        <>
          <p className="mb-4 text-label tabular-nums" aria-live="polite">
            {q.data.me?.rank ? `Você está em ${formatOrdinal(q.data.me.rank)} lugar, com ${formatPoints(q.data.me.points)}.` : "Você ainda não pontuou neste período."}
          </p>
          {q.data.items.length === 0 ? (
            <Card>
              <EmptyState icon={Trophy} title="Ranking vazio" description="O ranking começa com a primeira participação verificada." />
            </Card>
          ) : (
            <RankingList entries={q.data.items} meMembershipId={meEntry?.membership_id} />
          )}
        </>
      )}
      <details className="mt-6 text-label text-ink-secondary">
        <summary className="inline-flex min-h-11 cursor-pointer items-center">Como funciona o desempate</summary>
        <p className="max-w-[60ch] pb-2">{TIEBREAK_TEXT}</p>
      </details>
    </div>
  );
}
