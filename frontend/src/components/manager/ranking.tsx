"use client";

import { useQuery } from "@tanstack/react-query";
import { Trophy } from "lucide-react";
import { useState } from "react";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { SelectField, TextField } from "@/components/ui/fields";
import { Card, PageHeader, Pagination } from "@/components/ui/misc";
import { PERIOD_OPTIONS, RankingList, TIEBREAK_TEXT } from "@/components/shared/ranking-list";
import { teamApi } from "@/lib/api/manager";
import type { LeaderboardPeriod } from "@/lib/api/types";
import { keys } from "@/lib/queries";

const PAGE = 20;

export function ManagerRanking() {
  const [period, setPeriod] = useState<LeaderboardPeriod>("30d");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const q = useQuery({
    queryKey: [...keys.leaderboard, period],
    queryFn: () => teamApi.leaderboard({ period, limit: 100 }),
    staleTime: 30_000,
  });

  const all = q.data?.items ?? [];
  const term = search.trim().toLowerCase();
  const filtered = term ? all.filter((e) => e.name.toLowerCase().includes(term) || (e.instagram_username ?? "").toLowerCase().includes(term)) : all;
  const page = filtered.slice(offset, offset + PAGE);

  return (
    <>
      <PageHeader title="Ranking" description="Pontos ganhos no período. Trocar pontos por benefícios não reduz a posição." />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectField
          label="Período"
          value={period}
          onChange={(e) => {
            setPeriod(e.target.value as LeaderboardPeriod);
            setOffset(0);
          }}
        >
          {PERIOD_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Buscar promoter"
          type="search"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
      </div>

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
      ) : all.length === 0 ? (
        <Card>
          <EmptyState icon={Trophy} title="Ranking vazio" description="O ranking começa com a primeira participação verificada." />
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState title="Nenhum promoter encontrado" description="Tente outro nome ou @." />
        </Card>
      ) : (
        <>
          <RankingList entries={page} />
          <Pagination total={filtered.length} limit={PAGE} offset={offset} onChange={setOffset} />
        </>
      )}
      <details className="mt-6 text-label text-ink-secondary">
        <summary className="inline-flex min-h-11 cursor-pointer items-center">Como funciona o desempate</summary>
        <p className="max-w-[60ch] pb-2">{TIEBREAK_TEXT}</p>
      </details>
    </>
  );
}
