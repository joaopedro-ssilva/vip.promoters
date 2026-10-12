"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, Perforated, PointsChip, SectionTitle } from "@/components/ui/misc";
import { promoterApi } from "@/lib/api/promoter";
import { formatNumber, formatOrdinal, formatRelativeDay, formatSignedPoints } from "@/lib/format";
import { keys } from "@/lib/queries";
import { CampaignCard } from "./campaign-card";
import { TeamGate } from "./team-provider";

export function PromoterHomePage() {
  return (
    <>
      <h1 tabIndex={-1} className="sr-only">
        Início
      </h1>
      <TeamGate>{(orgId, m) => <Dashboard orgId={orgId} teamName={m.organization.name} />}</TeamGate>
    </>
  );
}

function Dashboard({ orgId, teamName }: { orgId: string; teamName: string }) {
  const q = useQuery({
    queryKey: [...keys.promoter(orgId), "home"],
    queryFn: () => promoterApi.home(orgId),
  });
  if (q.isPending) {
    return (
      <LoadingRegion className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_2fr]">
        <Skeleton className="h-56" />
        <Skeleton className="h-56" />
      </LoadingRegion>
    );
  }
  if (q.isError) {
    return (
      <Card>
        <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} message="Não foi possível atualizar agora. Seus dados foram mantidos. O saldo não é exibido até a atualização." />
      </Card>
    );
  }
  const d = q.data;
  const balance = d.membership.points_balance;
  const campaigns = d.active_campaigns.slice(0, 3);
  return (
    <div className="grid grid-cols-1 gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
      <div className="flex min-w-0 flex-col gap-6">
        <section aria-labelledby="saldo" className="vidro overflow-hidden rounded-card">
          <div className="p-6">
            <h2 id="saldo" className="rotulo">
              Saldo disponível
            </h2>
            <p className="cifra mt-3 text-balance text-success [overflow-wrap:anywhere]">
              {formatNumber(balance)}
            </p>
            <p className="mt-1 text-label font-normal text-ink-secondary">{balance === 1 ? "ponto" : "pontos"}</p>
            <Perforated className="my-4" />
            <div className="flex flex-wrap gap-x-4">
              <Link href="/promoter/extrato" className="inline-flex min-h-11 items-center text-label text-success hover:brightness-110">
                Ver extrato
              </Link>
              <Link href="/promoter/lojinha" className="inline-flex min-h-11 items-center text-label text-success hover:brightness-110">
                Ir para a lojinha
              </Link>
            </div>
            {d.affordable_rewards_count > 0 && (
              <p className="mt-1 text-caption text-ink-muted tabular-nums">
                {d.affordable_rewards_count} {d.affordable_rewards_count === 1 ? "recompensa" : "recompensas"} ao seu alcance.
              </p>
            )}
          </div>
        </section>

        <Card as="section" aria-labelledby="pos" className="md:p-6">
          <h2 id="pos" className="rotulo">
            Sua posição · {teamName}
          </h2>
          <p className="mt-1 font-sans text-page font-extrabold tabular-nums tracking-[-0.02em]">
            {d.rank ? `${formatOrdinal(d.rank)} lugar` : "Ainda sem posição"}
          </p>
          <p className="text-caption text-ink-muted tabular-nums">
            {d.rank ? `entre ${formatNumber(d.promoters_count)} ${d.promoters_count === 1 ? "promoter" : "promoters"} na equipe` : "A posição aparece com a primeira participação verificada."}
          </p>
          <Link href="/promoter/ranking" className="mt-2 inline-flex min-h-11 items-center text-label text-success underline">
            Ver ranking
          </Link>
        </Card>
      </div>

      <div className="flex min-w-0 flex-col gap-8">
        <section aria-labelledby="camp">
          <div className="mb-4 flex items-center justify-between gap-3">
            <SectionTitle id="camp">Campanhas ativas</SectionTitle>
            <Link href="/promoter/campanhas" className="text-label text-success underline">
              Ver todas
            </Link>
          </div>
          {campaigns.length === 0 ? (
            <Card>
              <EmptyState title="Nenhuma campanha ativa" description="Ainda não há campanhas ativas. Volte em breve para participar." />
            </Card>
          ) : (
            <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {campaigns.map((c) => (
                <CampaignCard key={c.id} c={c} />
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="trans">
          <div className="mb-4 flex items-center justify-between gap-3">
            <SectionTitle id="trans">Últimos lançamentos</SectionTitle>
            <Link href="/promoter/extrato" className="text-label text-success underline">
              Ver extrato
            </Link>
          </div>
          {d.recent_transactions.length === 0 ? (
            <Card>
              <EmptyState title="Nenhum lançamento ainda" description="Seu extrato começa na primeira participação verificada." />
            </Card>
          ) : (
            <ul className="overflow-hidden rounded-card border border-line-subtle">
              {d.recent_transactions.map((t) => (
                <li key={t.id} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-line-subtle bg-surface px-4 py-3 last:border-b-0">
                  <div className="min-w-0 flex-1 basis-48">
                    <p className="text-label [overflow-wrap:anywhere]">{t.description}</p>
                    <p className="text-caption text-ink-muted">{formatRelativeDay(t.created_at)}</p>
                  </div>
                  <PointsChip muted={t.amount < 0}>{formatSignedPoints(t.amount)}</PointsChip>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
