"use client";

import { useQuery } from "@tanstack/react-query";
import { Megaphone, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { ButtonLink, Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { TextField } from "@/components/ui/fields";
import { Card, FilterButtons, PageHeader, Pagination } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import { campaignsApi } from "@/lib/api/manager";
import type { Campaign } from "@/lib/api/types";
import { formatDate, isFuture, formatNumber, formatShortDateTime } from "@/lib/format";
import { keys } from "@/lib/queries";

const PAGE = 12;

type Filter = "all" | "active" | "draft" | "ended";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "active", label: "Ativas" },
  { value: "draft", label: "Rascunhos" },
  { value: "ended", label: "Encerradas" },
];

export function campaignPeriodNote(c: Pick<Campaign, "status" | "starts_at">): string | null {
  if (c.status === "active" && isFuture(c.starts_at)) {
    return `Começa em ${formatShortDateTime(c.starts_at)}`;
  }
  return null;
}

export function CampaignPeriod({ c }: { c: Pick<Campaign, "starts_at" | "ends_at"> }) {
  if (!c.starts_at && !c.ends_at) return <>Início ao disparar · sem data de término</>;
  return (
    <>
      {c.ends_at ? `${c.starts_at ? formatDate(c.starts_at) : "Ao disparar"} até ${formatDate(c.ends_at)}` : `${c.starts_at ? `A partir de ${formatDate(c.starts_at)}` : "Início ao disparar"} · sem data de término`}
    </>
  );
}

function CampaignCard({ c }: { c: Campaign }) {
  const note = campaignPeriodNote(c);
  return (
    <li className="flex min-w-0 flex-col gap-3 rounded-card border border-line-subtle bg-surface p-4">
      <RemoteImage src={c.thumbnail_url ?? c.media_url ?? c.publish_image_url} alt="" ratio="aspect-[4/3]" />
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge kind={c.status} campaign />
        {c.status === "draft" && <span className="text-caption text-ink-muted">Ainda não disponível para a equipe</span>}
      </div>
      <h3 className="line-clamp-2 font-sans text-body font-bold">{c.title}</h3>
      <p className="text-caption text-ink-muted tabular-nums">
        <CampaignPeriod c={c} />
      </p>
      {note && <p className="text-caption text-info">{note}</p>}
      <dl className="grid grid-cols-2 gap-3 border-t border-line-subtle pt-3">
        <div>
          <dt className="text-caption text-ink-muted">Comentários</dt>
          <dd className="text-label tabular-nums">{formatNumber(c.stats.comments_awarded)}</dd>
        </div>
        <div>
          <dt className="text-caption text-ink-muted">Menções</dt>
          <dd className="text-label tabular-nums">{formatNumber(c.stats.story_mentions_awarded)}</dd>
        </div>
      </dl>
      <div className="mt-auto">
        <Link href={`/gestor/campanhas/${c.id}`} className="inline-flex min-h-11 items-center text-label text-accent underline">
          Ver campanha<span className="sr-only">: {c.title}</span>
        </Link>
      </div>
    </li>
  );
}

export function CampaignsList() {
  const [filter, setFilter] = useState<Filter>("all");
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");

  const q = useQuery({
    queryKey: [...keys.campaigns, filter, offset],
    queryFn: () => campaignsApi.list({ status: filter === "all" ? undefined : filter, limit: PAGE, offset }),
    placeholderData: (prev) => prev,
  });

  const items = (q.data?.items ?? []).filter((c) => c.title.toLowerCase().includes(search.trim().toLowerCase()));
  const clear = () => {
    setFilter("all");
    setSearch("");
    setOffset(0);
  };

  return (
    <>
      <PageHeader
        title="Campanhas"
        actions={
          <ButtonLink href="/gestor/campanhas/nova" icon={Plus}>
            Nova campanha
          </ButtonLink>
        }
      />
      <div className="mb-6 flex flex-col gap-4">
        <TextField
          label="Filtrar por título"
          hint="Filtra apenas as campanhas desta página."
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
        <FilterButtons
          label="Situação"
          options={FILTERS}
          value={filter}
          onChange={(v) => {
            setFilter(v);
            setOffset(0);
          }}
        />
      </div>

      {q.isPending ? (
        <LoadingRegion className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-80" />
          ))}
        </LoadingRegion>
      ) : q.isError && !q.data ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : (q.data?.total ?? 0) === 0 ? (
        <Card>
          {filter === "all" ? (
            <EmptyState
              icon={Megaphone}
              title="Crie sua primeira campanha"
              description="Escolha um post do Instagram, defina os pontos e dispare para a equipe."
              action={
                <ButtonLink href="/gestor/campanhas/nova" icon={Plus}>
                  Nova campanha
                </ButtonLink>
              }
            />
          ) : (
            <EmptyState
              title="Nenhuma campanha encontrada"
              action={
                <Button variant="secondary" onClick={clear}>
                  Limpar filtros
                </Button>
              }
            />
          )}
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            title="Nenhuma campanha encontrada"
            description="Nenhum título desta página corresponde ao filtro."
            action={
              <Button variant="secondary" onClick={clear}>
                Limpar filtros
              </Button>
            }
          />
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" aria-busy={q.isFetching}>
          {items.map((c) => (
            <CampaignCard key={c.id} c={c} />
          ))}
        </ul>
      )}
      {q.data && <Pagination total={q.data.total} limit={PAGE} offset={offset} onChange={setOffset} busy={q.isFetching && q.isPlaceholderData} />}
    </>
  );
}
