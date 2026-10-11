"use client";

import { useQuery } from "@tanstack/react-query";
import { Megaphone } from "lucide-react";
import { useState } from "react";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, PageHeader, Tabs } from "@/components/ui/misc";
import { promoterApi } from "@/lib/api/promoter";
import { keys } from "@/lib/queries";
import { CampaignCard } from "./campaign-card";
import { TeamGate } from "./team-provider";

export function PromoterCampaigns() {
  return (
    <>
      <PageHeader title="Campanhas" />
      <TeamGate>{(orgId) => <List orgId={orgId} />}</TeamGate>
    </>
  );
}

function List({ orgId }: { orgId: string }) {
  const [tab, setTab] = useState<"active" | "ended">("active");
  const q = useQuery({
    queryKey: [...keys.promoter(orgId), "campaigns", tab],
    queryFn: () => promoterApi.campaigns(orgId, tab),
  });
  const items = q.data?.items ?? [];
  return (
    <Tabs
      label="Situação das campanhas"
      tabs={[
        { id: "active", label: "Ativas" },
        { id: "ended", label: "Encerradas" },
      ]}
      value={tab}
      onChange={setTab}
    >
      {q.isPending ? (
        <LoadingRegion className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </LoadingRegion>
      ) : q.isError ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={Megaphone}
            title={tab === "active" ? "Nenhuma campanha ativa" : "Nenhuma campanha encerrada"}
            description={tab === "active" ? "Ainda não há campanhas ativas. Volte em breve para participar." : undefined}
          />
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {items.map((c) => (
            <CampaignCard key={c.id} c={c} />
          ))}
        </ul>
      )}
    </Tabs>
  );
}
