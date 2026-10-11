"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Gift } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { FormError, SelectField } from "@/components/ui/fields";
import { Card, CopyButton, DialogActions, FilterButtons, PageHeader, Perforated, PointsChip } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import { ApiError } from "@/lib/api/client";
import { promoterApi } from "@/lib/api/promoter";
import type { PromoterReward, Redemption } from "@/lib/api/types";
import { formatNumber, formatPoints } from "@/lib/format";
import { keys } from "@/lib/queries";
import { TeamGate, useTeam } from "./team-provider";

export function PromoterShop() {
  return (
    <>
      <PageHeader title="Lojinha" />
      <TeamGate>{(orgId) => <Body orgId={orgId} />}</TeamGate>
    </>
  );
}

function Body({ orgId }: { orgId: string }) {
  const team = useTeam();
  const balance = team.active?.points_balance ?? 0;
  const [filter, setFilter] = useState<"all" | "can">("all");
  const [order, setOrder] = useState<"cost" | "recent">("cost");
  const [target, setTarget] = useState<PromoterReward | null>(null);

  const q = useQuery({
    queryKey: [...keys.promoter(orgId), "rewards"],
    queryFn: () => promoterApi.rewards(orgId),
  });

  const items = (q.data?.items ?? [])
    .filter((r) => filter === "all" || (r.can_afford && r.available))
    .sort((a, b) => (order === "cost" ? a.cost_points - b.cost_points : b.created_at.localeCompare(a.created_at)));

  return (
    <>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <p className="text-label">
          <span className="mr-2 text-ink-secondary">Saldo da equipe</span>
          <PointsChip>{formatPoints(balance)}</PointsChip>
        </p>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <FilterButtons
            label="Filtrar recompensas"
            options={[
              { value: "all", label: "Todas" },
              { value: "can", label: "Posso resgatar" },
            ]}
            value={filter}
            onChange={setFilter}
          />
          <SelectField label="Ordenar" value={order} onChange={(e) => setOrder(e.target.value as "cost" | "recent")} className="sm:w-44">
            <option value="cost">Menor custo</option>
            <option value="recent">Mais recentes</option>
          </SelectField>
        </div>
      </div>

      {q.isPending ? (
        <LoadingRegion className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-72" />
          ))}
        </LoadingRegion>
      ) : q.isError ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={Gift}
            title={filter === "can" ? "Nenhuma recompensa ao seu alcance" : "A lojinha ainda está vazia"}
            description={filter === "can" ? "Continue participando das campanhas para juntar pontos." : "O gestor ainda não cadastrou recompensas."}
          />
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((r) => {
            const missing = r.cost_points - balance;
            const soldOut = r.stock === 0;
            const limit = r.max_per_promoter !== null && r.my_redemptions_count >= r.max_per_promoter;
            const can = r.available && r.can_afford && !soldOut && !limit;
            return (
              <li key={r.id} className="flex min-w-0 flex-col gap-3 rounded-card border border-line-subtle bg-surface p-4">
                <RemoteImage src={r.image_url} fallbackLabel="Sem imagem" fallbackIcon={Gift} />
                <h3 className="font-sans text-body font-bold [overflow-wrap:anywhere]">{r.name}</h3>
                {r.description && <p className="line-clamp-3 text-label font-normal text-ink-secondary">{r.description}</p>}
                <div className="flex flex-wrap items-center gap-2">
                  <PointsChip>{formatPoints(r.cost_points)}</PointsChip>
                  {soldOut && <StatusBadge kind="sold_out" />}
                </div>
                <p className="text-caption text-ink-muted tabular-nums">
                  {r.stock === null ? "Estoque ilimitado" : soldOut ? "Sem estoque" : `${formatNumber(r.stock)} em estoque`}
                  {r.max_per_promoter ? ` · você resgatou ${r.my_redemptions_count} de ${r.max_per_promoter}` : ""}
                </p>
                <div className="mt-auto flex flex-col gap-1">
                  <Button block disabled={!can} onClick={() => setTarget(r)}>
                    Resgatar<span className="sr-only">: {r.name}</span>
                  </Button>
                  {!can && (
                    <p className="text-caption text-ink-muted tabular-nums">
                      {soldOut
                        ? "Esta recompensa está esgotada."
                        : limit
                          ? "Você atingiu o limite de resgates desta recompensa."
                          : !r.can_afford && missing > 0
                            ? `Faltam ${formatPoints(missing)} para este resgate.`
                            : "Indisponível no momento."}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <Dialog open={target !== null} onClose={() => setTarget(null)} title={target ? `Resgatar ${target.name}?` : "Resgatar"}>
        {target && <RedeemBody orgId={orgId} reward={target} balance={balance} onClose={() => setTarget(null)} />}
      </Dialog>
    </>
  );
}

function RedeemBody({ orgId, reward, balance, onClose }: { orgId: string; reward: PromoterReward; balance: number; onClose: () => void }) {
  const qc = useQueryClient();
  // a fresh id per dialog opening; kept for retries of the same submission
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<Redemption | null>(null);
  const [liveCost, setLiveCost] = useState(reward.cost_points);

  const m = useMutation({
    mutationFn: () => promoterApi.redeem(reward.id, requestId),
    onSuccess: async (r) => {
      setDone(r);
      await Promise.all([
        qc.invalidateQueries({ queryKey: keys.promoter(orgId) }),
        qc.invalidateQueries({ queryKey: keys.memberships }),
      ]);
    },
    onError: async (e) => {
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
        // a definitive business answer: nothing was debited; the next confirmation is a new submission
        setRequestId(crypto.randomUUID());
        setError(
          e.code === "out_of_stock"
            ? "Esta recompensa acabou de esgotar. Nenhum ponto foi descontado."
            : e.code === "insufficient_points"
              ? "Seu saldo mudou e não é suficiente para este resgate. Nenhum ponto foi descontado."
              : `${e.message} Nenhum ponto foi descontado.`,
        );
        await Promise.all([qc.invalidateQueries({ queryKey: keys.promoter(orgId) }), qc.invalidateQueries({ queryKey: keys.memberships })]);
        const fresh = qc.getQueryData<{ items: PromoterReward[] }>([...keys.promoter(orgId), "rewards"]);
        const cur = fresh?.items.find((x) => x.id === reward.id);
        if (cur) setLiveCost(cur.cost_points);
      } else {
        // unknown outcome (network / 5xx): keep the same request id so a retry cannot double-charge
        setError("Estamos confirmando o resultado. Consulte Meus resgates antes de tentar novamente.");
      }
    },
  });

  const shownBalance = balance;

  if (done) {
    return (
      <div className="flex flex-col gap-4">
        <p role="status" className="flex items-start gap-2 text-body text-success">
          <CircleCheck aria-hidden="true" strokeWidth={1.75} className="mt-1 size-5 shrink-0" />
          Resgate confirmado. Apresente seu código ao gestor.
        </p>
        <div className="rounded-control border border-line bg-surface-raised p-4">
          <p className="text-caption text-ink-muted">{done.reward.name}</p>
          <Perforated className="my-3" />
          <div className="flex items-center justify-between gap-2">
            <p className="text-section font-bold tracking-[0.08em] tabular-nums [overflow-wrap:anywhere]">{done.code}</p>
            <CopyButton text={done.code} label="Copiar código" successMessage="Código copiado." iconOnly />
          </div>
        </div>
        <DialogActions>
          <Button variant="secondary" onClick={onClose} data-autofocus="">
            Fechar
          </Button>
          <Link href="/promoter/resgates" className="inline-flex min-h-12 items-center justify-center rounded-control border border-accent bg-accent px-4 text-label text-on-accent hover:bg-accent-hover">
            Ver meus resgates
          </Link>
        </DialogActions>
      </div>
    );
  }

  const after = shownBalance - liveCost;
  return (
    <div className="flex flex-col gap-4">
      <p className="text-body text-ink-secondary">
        Resgatar {reward.name} por {formatPoints(liveCost)}?
      </p>
      <dl className="grid grid-cols-1 gap-2 rounded-control bg-surface-raised p-3 text-label tabular-nums">
        <div className="flex justify-between gap-3">
          <dt>Custo</dt>
          <dd>{formatPoints(liveCost)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>Seu saldo</dt>
          <dd>{formatPoints(shownBalance)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>Depois do resgate</dt>
          <dd>{after >= 0 ? formatPoints(after) : "Saldo insuficiente"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>Quantidade</dt>
          <dd>1</dd>
        </div>
      </dl>
      <FormError message={error} />
      <DialogActions>
        <Button variant="secondary" onClick={onClose} disabled={m.isPending}>
          Voltar
        </Button>
        <Button
          loading={m.isPending}
          disabled={after < 0}
          data-autofocus=""
          onClick={() => {
            setError(null);
            m.mutate();
          }}
        >
          {m.isPending ? "Resgatando…" : "Confirmar resgate"}
        </Button>
      </DialogActions>
    </div>
  );
}
