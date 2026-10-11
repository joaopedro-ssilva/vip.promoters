"use client";

import { useQuery } from "@tanstack/react-query";
import { Ticket } from "lucide-react";
import { useState } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, CopyButton, PageHeader, Perforated, Tabs } from "@/components/ui/misc";
import { promoterApi } from "@/lib/api/promoter";
import type { Redemption } from "@/lib/api/types";
import { formatDateTime, formatPoints } from "@/lib/format";
import { keys } from "@/lib/queries";
import { TeamGate } from "./team-provider";

export function PromoterRedemptions() {
  return (
    <>
      <PageHeader title="Meus resgates" />
      <TeamGate>{(orgId) => <Body orgId={orgId} />}</TeamGate>
    </>
  );
}

function Body({ orgId }: { orgId: string }) {
  const [tab, setTab] = useState<"pending" | "history">("pending");
  const q = useQuery({
    queryKey: [...keys.promoter(orgId), "redemptions"],
    queryFn: () => promoterApi.redemptions(orgId, 100, 0),
  });
  const all = q.data?.items ?? [];
  const items = all.filter((r) => (tab === "pending" ? r.status === "pending" : r.status !== "pending"));
  return (
    <Tabs
      label="Resgates"
      tabs={[
        { id: "pending", label: "Pendentes" },
        { id: "history", label: "Histórico" },
      ]}
      value={tab}
      onChange={setTab}
    >
      {q.isPending ? (
        <LoadingRegion className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </LoadingRegion>
      ) : q.isError ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : all.length === 0 ? (
        <Card>
          <EmptyState icon={Ticket} title="Você ainda não resgatou benefícios" action={<ButtonLink href="/promoter/lojinha">Ver lojinha</ButtonLink>} />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState title={tab === "pending" ? "Nenhum resgate pendente" : "Histórico vazio"} />
        </Card>
      ) : (
        <>
          <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {items.map((r) => (
              <RedemptionCard key={r.id} r={r} />
            ))}
          </ul>
          {q.data && q.data.total > all.length && <p className="mt-4 text-caption text-ink-muted">Mostrando os {all.length} resgates mais recentes.</p>}
        </>
      )}
    </Tabs>
  );
}

function RedemptionCard({ r }: { r: Redemption }) {
  return (
    <li className="min-w-0 rounded-card border border-line-subtle bg-surface p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 font-sans text-body font-bold [overflow-wrap:anywhere]">{r.reward.name}</h3>
        <StatusBadge kind={r.status} />
      </div>
      <p className="mt-1 text-caption text-ink-muted tabular-nums">
        {formatPoints(r.cost_points)} · {formatDateTime(r.created_at)}
        {r.organization_name ? ` · ${r.organization_name}` : ""}
      </p>
      <Perforated className="my-4" />
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 text-section font-bold tracking-[0.08em] tabular-nums [overflow-wrap:anywhere]">{r.code}</p>
        <CopyButton text={r.code} label="Copiar código" successMessage="Código copiado." />
      </div>
      {r.status === "pending" && (
        <p className="mt-3 rounded-control bg-surface-raised p-3 text-label font-normal text-ink-secondary">Apresente este código ao gestor.</p>
      )}
      {r.status === "fulfilled" && r.resolved_at && <p className="mt-3 text-label font-normal text-success">Entregue em {formatDateTime(r.resolved_at)}.</p>}
      {r.status === "cancelled" && <p className="mt-3 text-label font-normal text-ink-secondary">Pontos devolvidos.</p>}
      {r.note && <p className="mt-2 text-caption text-ink-muted [overflow-wrap:anywhere]">Observação: {r.note}</p>}
    </li>
  );
}
