"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, FilterButtons, PointsChip, Pagination } from "@/components/ui/misc";
import { promoterApi } from "@/lib/api/promoter";
import type { PointTransaction } from "@/lib/api/types";
import { brasiliaDayKey, formatDate, formatNumber, formatPoints, formatSignedPoints, formatTime, formatYmdLong } from "@/lib/format";
import { cn } from "@/lib/cn";
import { keys } from "@/lib/queries";
import { TeamGate, useTeam } from "./team-provider";

const PAGE = 20;

export function PromoterStatement() {
  return (
    <>
      <Link href="/promoter" className="mb-4 inline-flex min-h-11 items-center gap-2 text-label text-ink-secondary hover:text-ink">
        <ArrowLeft aria-hidden="true" strokeWidth={1.75} className="size-4" />
        Início
      </Link>
      <h1 tabIndex={-1} className="mb-6 font-heading text-page lg:text-page-wide outline-none">
        Extrato de pontos
      </h1>
      <TeamGate>{(orgId) => <Body orgId={orgId} />}</TeamGate>
    </>
  );
}

const TYPE_LABEL: Record<PointTransaction["type"], string> = {
  earn: "Entrada",
  redeem: "Resgate",
  refund: "Estorno",
  adjust: "Ajuste",
};

function Body({ orgId }: { orgId: string }) {
  const team = useTeam();
  const [offset, setOffset] = useState(0);
  const [kind, setKind] = useState<"all" | "in" | "out">("all");
  const q = useQuery({
    queryKey: [...keys.promoter(orgId), "transactions", offset],
    queryFn: () => promoterApi.transactions(orgId, PAGE, offset),
    placeholderData: (prev) => prev,
  });
  const items = (q.data?.items ?? []).filter((t) => (kind === "all" ? true : kind === "in" ? t.amount > 0 : t.amount < 0));

  const groups = new Map<string, PointTransaction[]>();
  for (const t of items) {
    const k = brasiliaDayKey(t.created_at);
    groups.set(k, [...(groups.get(k) ?? []), t]);
  }

  return (
    <>
      <p className="mb-4 text-label">
        <span className="mr-2 text-ink-secondary">Saldo atual</span>
        <PointsChip>{formatPoints(team.active?.points_balance ?? 0)}</PointsChip>
      </p>
      <div className="mb-6">
        <FilterButtons
          label="Tipo de lançamento"
          options={[
            { value: "all", label: "Todas" },
            { value: "in", label: "Entradas" },
            { value: "out", label: "Saídas" },
          ]}
          value={kind}
          onChange={setKind}
        />
        <p className="mt-2 text-caption text-ink-muted">O filtro vale para os lançamentos desta página.</p>
      </div>

      {q.isPending ? (
        <LoadingRegion className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </LoadingRegion>
      ) : q.isError && !q.data ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : (q.data?.total ?? 0) === 0 ? (
        <Card>
          <EmptyState title="Extrato vazio" description="Seu extrato começa na primeira participação verificada." />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState title="Nenhum lançamento nesta página" description="Tente outro filtro." />
        </Card>
      ) : (
        <div className="flex flex-col gap-6" aria-busy={q.isFetching}>
          {[...groups.entries()].map(([day, list]) => (
            <section key={day} aria-label={formatYmdLong(day)}>
              <h2 className="mb-2 text-label text-ink-secondary tabular-nums">{formatDate(list[0].created_at)}</h2>
              <ul className="overflow-hidden rounded-card border border-line-subtle">
                {list.map((t) => (
                  <li key={t.id} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 border-b border-line-subtle bg-surface px-4 py-3 last:border-b-0">
                    <div className="min-w-0 flex-1 basis-48">
                      <p className="text-label [overflow-wrap:anywhere]">{t.description}</p>
                      <p className="text-caption text-ink-muted tabular-nums">
                        {TYPE_LABEL[t.type]} · {formatTime(t.created_at)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className={cn(
                          "text-label tabular-nums",
                          t.amount > 0 ? (t.type === "refund" ? "text-info" : "text-success") : "text-ink-secondary",
                        )}
                      >
                        {formatSignedPoints(t.amount)}
                      </p>
                      <p className="text-caption text-ink-muted tabular-nums">Saldo: {formatNumber(t.balance_after)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
      {q.data && <Pagination total={q.data.total} limit={PAGE} offset={offset} onChange={setOffset} busy={q.isFetching && q.isPlaceholderData} />}
    </>
  );
}
