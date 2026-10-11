"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ticket } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { FormError, TextareaField, TextField } from "@/components/ui/fields";
import { Card, CopyButton, DialogActions, FilterButtons, PageHeader, Pagination, PointsChip } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { ApiError, errorMessage } from "@/lib/api/client";
import { redemptionsApi } from "@/lib/api/manager";
import type { Redemption, RedemptionStatus } from "@/lib/api/types";
import { formatDateTime, formatNumber, formatPoints } from "@/lib/format";
import { keys } from "@/lib/queries";

const PAGE = 20;
const FILTERS: { value: RedemptionStatus; label: string }[] = [
  { value: "pending", label: "Pendentes" },
  { value: "fulfilled", label: "Cumpridos" },
  { value: "cancelled", label: "Cancelados" },
];

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

function useCount(status: RedemptionStatus) {
  return useQuery({
    queryKey: [...keys.redemptions, "count", status],
    queryFn: () => redemptionsApi.list({ status, limit: 1 }),
    staleTime: 30_000,
    select: (d) => d.total,
  });
}

export function RedemptionsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [status, setStatus] = useState<RedemptionStatus>("pending");
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const debounced = useDebounced(search.trim());
  const [action, setAction] = useState<{ kind: "fulfill" | "cancel"; item: Redemption } | null>(null);

  const q = useQuery({
    queryKey: [...keys.redemptions, "list", status, debounced, offset],
    queryFn: () => redemptionsApi.list({ status, search: debounced || undefined, limit: PAGE, offset }),
    placeholderData: (prev) => prev,
  });
  const cPending = useCount("pending");
  const cFul = useCount("fulfilled");
  const cCan = useCount("cancelled");
  const counts: Record<RedemptionStatus, number | undefined> = { pending: cPending.data, fulfilled: cFul.data, cancelled: cCan.data };

  const items = useMemo(() => {
    const list = q.data?.items ?? [];
    // the pending queue is worked oldest first
    return status === "pending" ? [...list].sort((a, b) => a.created_at.localeCompare(b.created_at)) : list;
  }, [q.data, status]);

  const refresh = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: keys.redemptions }),
      qc.invalidateQueries({ queryKey: keys.dashboard }),
      qc.invalidateQueries({ queryKey: keys.rewards }),
      qc.invalidateQueries({ queryKey: keys.members }),
    ]);
  };

  const handleConflict = async (e: unknown): Promise<boolean> => {
    if (e instanceof ApiError && (e.code === "redemption_not_pending" || e.status === 409)) {
      toast.info("Este resgate já foi atualizado. Atualizamos os dados para você.");
      await refresh();
      return true;
    }
    return false;
  };

  return (
    <>
      <PageHeader title="Resgates" description="Confira a pessoa e o código antes de entregar o benefício." />
      <div className="mb-6 flex flex-col gap-4">
        <TextField
          label="Buscar por código ou nome"
          type="search"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="max-w-md"
        />
        <FilterButtons
          label="Situação"
          options={FILTERS.map((f) => ({
            value: f.value,
            label: counts[f.value] !== undefined ? `${f.label} (${formatNumber(counts[f.value]!)})` : f.label,
          }))}
          value={status}
          onChange={(v) => {
            setStatus(v);
            setOffset(0);
          }}
        />
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
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={Ticket}
            title={debounced ? "Nenhum resgate encontrado" : status === "pending" ? "Nenhum resgate pendente" : "Nada por aqui"}
            description={debounced ? "Tente outro código ou nome." : status === "pending" ? "Tudo em dia. Novos resgates aparecem aqui." : undefined}
          />
        </Card>
      ) : (
        <>
          <div className="hidden md:block" aria-busy={q.isFetching}>
            <table className="w-full border-collapse overflow-hidden rounded-card border border-line-subtle text-left">
              <caption className="sr-only">Resgates</caption>
              <thead className="bg-surface-raised text-label text-ink-secondary">
                <tr>
                  <th scope="col" className="px-4 py-3 font-semibold">Código</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Pessoa</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Recompensa</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">Custo</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Data</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Status</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Ações</th>
                </tr>
              </thead>
              <tbody className="bg-surface">
                {items.map((r) => (
                  <tr key={r.id} className="border-t border-line-subtle">
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1">
                        <Code code={r.code} />
                        <CopyButton text={r.code} label={`Copiar código ${r.code}`} successMessage="Código copiado." iconOnly />
                      </span>
                    </td>
                    <td className="px-4 py-3 text-label [overflow-wrap:anywhere]">
                      {r.promoter?.name ?? "—"}
                      {r.promoter && <span className="block text-caption font-normal text-ink-muted">@{r.promoter.instagram_username}</span>}
                    </td>
                    <td className="px-4 py-3 text-label font-normal [overflow-wrap:anywhere]">{r.reward.name}</td>
                    <td className="px-4 py-3 text-right text-label tabular-nums">{formatPoints(r.cost_points)}</td>
                    <td className="px-4 py-3 text-label font-normal tabular-nums">{formatDateTime(r.created_at)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge kind={r.status} />
                    </td>
                    <td className="px-4 py-3">
                      <RowActions r={r} onAction={(kind) => setAction({ kind, item: r })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="flex flex-col gap-3 md:hidden" aria-busy={q.isFetching}>
            {items.map((r) => (
              <li key={r.id} className="min-w-0 rounded-card border border-line-subtle bg-surface p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex min-w-0 items-center gap-1">
                    <Code code={r.code} />
                    <CopyButton text={r.code} label={`Copiar código ${r.code}`} successMessage="Código copiado." iconOnly />
                  </span>
                  <StatusBadge kind={r.status} />
                </div>
                <p className="mt-2 text-body font-bold [overflow-wrap:anywhere]">{r.reward.name}</p>
                <p className="text-label font-normal text-ink-secondary [overflow-wrap:anywhere]">
                  {r.promoter?.name ?? "—"} {r.promoter && `(@${r.promoter.instagram_username})`}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-ink-muted tabular-nums">
                  <PointsChip muted>{formatPoints(r.cost_points)}</PointsChip>
                  <span>{formatDateTime(r.created_at)}</span>
                </div>
                {r.status === "pending" && (
                  <div className="mt-3 border-t border-line-subtle pt-3">
                    <RowActions r={r} onAction={(kind) => setAction({ kind, item: r })} />
                  </div>
                )}
              </li>
            ))}
          </ul>
          {q.data && <Pagination total={q.data.total} limit={PAGE} offset={offset} onChange={setOffset} busy={q.isFetching && q.isPlaceholderData} />}
        </>
      )}

      <Dialog
        open={action !== null}
        onClose={() => setAction(null)}
        title={action?.kind === "fulfill" ? "Confirmar entrega" : "Cancelar resgate"}
        description={
          action?.kind === "fulfill"
            ? "Confira a pessoa e o código antes de confirmar a entrega."
            : "Cancelar este resgate? Os pontos e a unidade voltarão ao saldo e ao estoque."
        }
      >
        {action && (
          <ActionForm
            kind={action.kind}
            item={action.item}
            onClose={() => setAction(null)}
            onDone={async () => {
              await refresh();
              toast.success(action.kind === "fulfill" ? "Entrega confirmada." : "Resgate cancelado. Pontos devolvidos.");
            }}
            onConflict={handleConflict}
          />
        )}
      </Dialog>
    </>
  );
}

function Code({ code }: { code: string }) {
  return <span className="text-label font-bold tracking-[0.08em] tabular-nums [overflow-wrap:anywhere]">{code}</span>;
}

function RowActions({ r, onAction }: { r: Redemption; onAction: (k: "fulfill" | "cancel") => void }) {
  if (r.status !== "pending") {
    return <span className="text-caption text-ink-muted">{r.resolved_at ? formatDateTime(r.resolved_at) : "—"}</span>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      <Button size="sm" onClick={() => onAction("fulfill")}>
        Cumprir<span className="sr-only"> resgate {r.code}</span>
      </Button>
      <Button size="sm" variant="ghost" onClick={() => onAction("cancel")}>
        Cancelar<span className="sr-only"> resgate {r.code}</span>
      </Button>
    </div>
  );
}

function ActionForm({
  kind,
  item,
  onClose,
  onDone,
  onConflict,
}: {
  kind: "fulfill" | "cancel";
  item: Redemption;
  onClose: () => void;
  onDone: () => Promise<void>;
  onConflict: (e: unknown) => Promise<boolean>;
}) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: () => (kind === "fulfill" ? redemptionsApi.fulfill(item.id, note.trim() || undefined) : redemptionsApi.cancel(item.id, note.trim() || undefined)),
    onSuccess: async () => {
      await onDone();
      onClose();
    },
    onError: async (e) => {
      if (await onConflict(e)) onClose();
      else setError(errorMessage(e));
    },
  });
  const tooLong = note.length > 500;
  return (
    <form
      noValidate
      onSubmit={(ev) => {
        ev.preventDefault();
        if (tooLong) return;
        setError(null);
        m.mutate();
      }}
      className="flex flex-col gap-4"
    >
      <dl className="grid grid-cols-1 gap-3 rounded-control bg-surface-raised p-3 text-label">
        <div>
          <dt className="text-caption text-ink-muted">Código</dt>
          <dd className="font-bold tracking-[0.08em] tabular-nums">{item.code}</dd>
        </div>
        <div>
          <dt className="text-caption text-ink-muted">Pessoa</dt>
          <dd className="[overflow-wrap:anywhere]">
            {item.promoter ? `${item.promoter.name} (@${item.promoter.instagram_username})` : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-caption text-ink-muted">Recompensa</dt>
          <dd className="[overflow-wrap:anywhere]">
            {item.reward.name} · {formatPoints(item.cost_points)}
          </dd>
        </div>
      </dl>
      <TextareaField
        label="Observação"
        optional
        data-autofocus=""
        value={note}
        onChange={(e) => setNote(e.target.value)}
        hint={`${note.length} de 500 caracteres`}
        error={tooLong ? "A observação pode ter no máximo 500 caracteres." : undefined}
      />
      <FormError message={error} />
      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          Voltar
        </Button>
        <Button type="submit" variant={kind === "cancel" ? "danger" : "primary"} loading={m.isPending}>
          {m.isPending ? "Enviando…" : kind === "fulfill" ? "Confirmar entrega" : "Cancelar resgate"}
        </Button>
      </DialogActions>
    </form>
  );
}
