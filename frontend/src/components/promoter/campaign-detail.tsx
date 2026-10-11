"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { StatusBadge, type BadgeKind } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, CopyButton, PointsChip } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import { ApiError } from "@/lib/api/client";
import { promoterApi } from "@/lib/api/promoter";
import type { Interaction } from "@/lib/api/types";
import { formatDateTime, formatShortDateTime, formatSignedPoints } from "@/lib/format";
import { keys } from "@/lib/queries";
import { Checklist } from "./campaign-card";
import { useTeam } from "./team-provider";

const KIND: Record<Interaction["status"], BadgeKind> = {
  awarded: "awarded",
  duplicate: "duplicate",
  unmatched: "unmatched",
  out_of_window: "out_of_window",
};

export function PromoterCampaignDetailView({ id }: { id: string }) {
  const team = useTeam();
  const q = useQuery({ queryKey: [...keys.promoter(team.activeOrgId ?? "none"), "campaign", id], queryFn: () => promoterApi.campaign(id), enabled: team.status === "ready" });

  const back = (
    <Link href="/promoter/campanhas" className="mb-6 inline-flex min-h-11 items-center gap-2 text-label text-ink-secondary hover:text-ink">
      <ArrowLeft aria-hidden="true" strokeWidth={1.75} className="size-4" />
      Campanhas
    </Link>
  );

  if (q.isPending) {
    return (
      <div>
        {back}
        <LoadingRegion className="flex flex-col gap-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64" />
        </LoadingRegion>
      </div>
    );
  }
  if (q.isError) {
    const nf = q.error instanceof ApiError && q.error.status === 404;
    return (
      <div>
        {back}
        <Card>
          {nf ? <EmptyState title="Campanha não encontrada" /> : <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />}
        </Card>
      </div>
    );
  }
  const c = q.data;
  const handle = team.memberships.find((m) => m.organization.id === c.organization_id)?.organization.instagram_username;
  const ended = c.status === "ended";
  return (
    <div>
      {back}
      <div className="grid grid-cols-1 gap-8 md:grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
        <RemoteImage src={c.media_url ?? c.thumbnail_url} />
        <div className="min-w-0">
          <StatusBadge kind={c.status} campaign />
          <h1 tabIndex={-1} className="mt-2 font-heading text-page lg:text-page-wide outline-none">
            {c.title}
          </h1>
          <p className="mt-2 text-label text-ink-secondary tabular-nums">
            {c.ends_at ? `${ended ? "Encerrou" : "Termina"} em ${formatShortDateTime(c.ends_at)}` : "Sem data de término"} · Horário de Brasília
          </p>
          {c.description && <p className="mt-4 whitespace-pre-wrap text-body text-ink-secondary">{c.description}</p>}
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card as="section" aria-labelledby="como">
          <h2 id="como" className="mb-3 font-heading text-section">
            Como participar
          </h2>
          {c.instructions && <p className="mb-4 whitespace-pre-wrap text-body text-ink-secondary">{c.instructions}</p>}
          <Checklist c={c} />
          {c.points_story_mention > 0 && handle && !ended && (
            <p className="mt-4 flex flex-wrap items-center gap-2 text-label font-normal text-ink-secondary">
              Publique um story e mencione @{handle}
              <CopyButton text={`@${handle}`} label="Copiar @" successMessage="@ copiado." />
            </p>
          )}
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            {ended ? (
              <Button variant="secondary" disabled>
                Campanha encerrada
              </Button>
            ) : (
              c.permalink && (
                <ButtonLink href={c.permalink} external variant="secondary">
                  Abrir no Instagram
                </ButtonLink>
              )
            )}
            <Button variant="ghost" icon={RefreshCw} loading={q.isFetching} onClick={() => q.refetch()}>
              {q.isFetching ? "Atualizando…" : "Atualizar participações"}
            </Button>
          </div>
          <p className="mt-2 text-caption text-ink-muted">A verificação pode levar alguns minutos. Abrir o post ou atualizar não concede pontos por si.</p>
        </Card>

        <Card as="section" aria-labelledby="minhas">
          <h2 id="minhas" className="mb-3 font-heading text-section">
            Minhas participações
          </h2>
          {c.my_interactions.length === 0 ? (
            <p className="text-label font-normal text-ink-secondary">Nenhuma participação verificada ainda.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {c.my_interactions.map((i) => (
                <li key={i.id} className="rounded-control bg-surface-raised p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-label">{i.type === "comment" ? "Comentário" : "Menção em story"}</span>
                    <span className="flex flex-wrap items-center gap-2">
                      <StatusBadge kind={KIND[i.status]} />
                      {i.status === "awarded" && i.points_awarded > 0 && <PointsChip>{formatSignedPoints(i.points_awarded)}</PointsChip>}
                    </span>
                  </div>
                  <p className="mt-1 text-caption text-ink-muted tabular-nums">{formatDateTime(i.occurred_at)}</p>
                  {i.status === "duplicate" && (
                    <p className="mt-1 text-label font-normal text-warning">
                      {i.type === "comment"
                        ? "Este comentário não gerou pontos. Você já pontuou com um comentário nesta campanha."
                        : "Você já pontuou com uma menção em story nesta campanha."}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
