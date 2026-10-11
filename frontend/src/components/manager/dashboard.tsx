"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleCheck, Coins, Info, Megaphone, MessageSquare, Plus, Users } from "lucide-react";
import Link from "next/link";
import { ButtonLink, Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, Kpi, PageHeader, SectionTitle } from "@/components/ui/misc";
import { RankingList } from "@/components/shared/ranking-list";
import { useConnectInstagram } from "@/components/shared/use-connect-instagram";
import { formatNumber } from "@/lib/format";
import { managerDashboardQuery } from "@/lib/queries";
import { InteractionItem } from "./interaction-item";
import { InteractionsChart } from "./interactions-chart";

export function ManagerDashboard() {
  const q = useQuery(managerDashboardQuery());
  const connect = useConnectInstagram();
  const d = q.data;

  return (
    <>
      <PageHeader
        title="Visão geral"
        actions={
          <ButtonLink href="/gestor/campanhas/nova" icon={Plus}>
            Nova campanha
          </ButtonLink>
        }
      />

      {q.isError && !d ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : (
        <div className="flex flex-col gap-8">
          {d && !d.instagram_connected && (
            <section aria-labelledby="ig-banner" className="flex flex-col gap-3 rounded-card border border-line-subtle bg-surface-raised p-4 md:flex-row md:items-center md:justify-between md:p-6">
              <div className="flex min-w-0 items-start gap-3">
                <Info aria-hidden="true" strokeWidth={1.75} className="mt-1 size-5 shrink-0 text-info" />
                <div className="min-w-0">
                  <h2 id="ig-banner" className="font-heading text-section">
                    Conecte o Instagram para começar
                  </h2>
                  <p className="text-body text-ink-secondary">
                    Sem a conexão não é possível selecionar publicações nem verificar participações. Você pode salvar rascunhos antes.
                  </p>
                </div>
              </div>
              <Button loading={connect.isPending} onClick={() => connect.mutate()}>
                {connect.isPending ? "Conectando…" : "Conectar Instagram"}
              </Button>
            </section>
          )}

          <section aria-label="Indicadores" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Kpi label="Campanhas ativas" value={d?.kpis.campaigns_active} help="Total atual" icon={Megaphone} loading={q.isPending} />
            <Kpi label="Promoters aprovados" value={d?.kpis.promoters_approved} help="Total atual" icon={Users} loading={q.isPending} />
            <Kpi label="Interações pontuadas" value={d?.kpis.interactions_7d} help="Últimos 7 dias" icon={MessageSquare} loading={q.isPending} />
            <Kpi label="Pontos distribuídos" value={d?.kpis.points_issued_30d} help="Últimos 30 dias" icon={Coins} loading={q.isPending} />
          </section>

          <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <Card as="section" aria-labelledby="chart-title">
              <SectionTitle id="chart-title" className="mb-1">
                Interações por dia
              </SectionTitle>
              <p className="mb-4 text-label text-ink-secondary">Últimos 14 dias, comentários e menções em story pontuados.</p>
              {q.isPending ? (
                <LoadingRegion>
                  <Skeleton className="h-[200px] md:h-[240px]" />
                </LoadingRegion>
              ) : d ? (
                <InteractionsChart data={d.interactions_by_day} />
              ) : null}
            </Card>

            <Card as="section" aria-labelledby="pending-title">
              <SectionTitle id="pending-title" className="mb-4">
                Pendências
              </SectionTitle>
              {q.isPending ? (
                <LoadingRegion className="flex flex-col gap-3">
                  <Skeleton className="h-12" />
                  <Skeleton className="h-12" />
                </LoadingRegion>
              ) : d ? (
                d.kpis.promoters_pending === 0 && d.kpis.redemptions_pending === 0 ? (
                  <p className="flex items-center gap-2 text-body text-success">
                    <CircleCheck aria-hidden="true" strokeWidth={1.75} className="size-5" />
                    Tudo em dia
                  </p>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {d.kpis.promoters_pending > 0 && (
                      <li className="flex flex-wrap items-center justify-between gap-2 rounded-control bg-surface-raised p-3">
                        <span className="min-w-0 text-label tabular-nums">
                          {formatNumber(d.kpis.promoters_pending)} {d.kpis.promoters_pending === 1 ? "promoter aguardando" : "promoters aguardando"} aprovação
                        </span>
                        <ButtonLink href="/gestor/equipe" size="sm" variant="secondary">
                          Aprovar promoters
                        </ButtonLink>
                      </li>
                    )}
                    {d.kpis.redemptions_pending > 0 && (
                      <li className="flex flex-wrap items-center justify-between gap-2 rounded-control bg-surface-raised p-3">
                        <span className="min-w-0 text-label tabular-nums">
                          {formatNumber(d.kpis.redemptions_pending)} {d.kpis.redemptions_pending === 1 ? "resgate pendente" : "resgates pendentes"}
                        </span>
                        <ButtonLink href="/gestor/resgates" size="sm" variant="secondary">
                          Ver resgates
                        </ButtonLink>
                      </li>
                    )}
                  </ul>
                )
              ) : null}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
            <section aria-labelledby="top-title">
              <div className="mb-4 flex items-center justify-between gap-3">
                <SectionTitle id="top-title">Top promoters</SectionTitle>
                <Link href="/gestor/ranking" className="text-label text-accent underline">
                  Ver ranking
                </Link>
              </div>
              {q.isPending ? (
                <LoadingRegion className="flex flex-col gap-2">
                  {Array.from({ length: 5 }, (_, i) => (
                    <Skeleton key={i} className="h-[4.5rem]" />
                  ))}
                </LoadingRegion>
              ) : d && d.top_promoters.length > 0 ? (
                <RankingList entries={d.top_promoters} />
              ) : (
                <Card>
                  <EmptyState title="Sem ranking ainda" description="O ranking começa com a primeira participação verificada." />
                </Card>
              )}
            </section>

            <section aria-labelledby="recent-title">
              <SectionTitle id="recent-title" className="mb-4">
                Interações recentes
              </SectionTitle>
              {q.isPending ? (
                <LoadingRegion className="flex flex-col gap-2">
                  {Array.from({ length: 4 }, (_, i) => (
                    <Skeleton key={i} className="h-24" />
                  ))}
                </LoadingRegion>
              ) : d && d.recent_interactions.length > 0 ? (
                <ul className="flex flex-col gap-2">
                  {d.recent_interactions.map((i) => (
                    <InteractionItem key={i.id} item={i} showCampaignLink />
                  ))}
                </ul>
              ) : (
                <Card>
                  <EmptyState title="Nenhuma interação ainda" description="As participações dos promoters aparecem aqui assim que forem verificadas." />
                </Card>
              )}
            </section>
          </div>
        </div>
      )}
    </>
  );
}
