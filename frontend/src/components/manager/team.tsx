"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, RotateCw, UserRoundSearch, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog, useDialogDirty } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { FormError, TextField } from "@/components/ui/fields";
import { Avatar, Card, CopyButton, DialogActions, FilterButtons, PageHeader, Pagination } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { teamApi } from "@/lib/api/manager";
import type { Member, MembershipStatus } from "@/lib/api/types";
import { formatDate, formatNumber, formatPoints } from "@/lib/format";
import { applyServerError } from "@/lib/form";
import { keys } from "@/lib/queries";
import { safeUrl } from "@/lib/safe-url";
import { parseIntStrict } from "@/lib/validation";

const PAGE = 20;
type Filter = "all" | "pending" | "approved";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "pending", label: "Pendentes" },
  { value: "approved", label: "Aprovados" },
];

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

type Action = { kind: "reject" | "remove" | "adjust"; member: Member } | null;

export function TeamPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState<Filter>("all");
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const debounced = useDebounced(search.trim());
  const [action, setAction] = useState<Action>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rotateOpen, setRotateOpen] = useState(false);
  const [rotateError, setRotateError] = useState<string | null>(null);

  const invite = useQuery({ queryKey: keys.invite, queryFn: teamApi.invite, staleTime: 60_000 });
  const approvedCount = useQuery({
    queryKey: [...keys.members, "approved-count"],
    queryFn: () => teamApi.members({ status: "approved", limit: 1 }),
    staleTime: 30_000,
  });

  const members = useQuery({
    queryKey: [...keys.members, filter, debounced, offset],
    queryFn: () =>
      teamApi.members({
        status: filter === "all" ? undefined : (filter as MembershipStatus),
        search: debounced || undefined,
        limit: PAGE,
        offset,
      }),
    placeholderData: (prev) => prev,
  });

  const afterChange = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: keys.members }),
      qc.invalidateQueries({ queryKey: keys.dashboard }),
      qc.invalidateQueries({ queryKey: keys.leaderboard }),
    ]);
  };

  const approve = useMutation({
    mutationFn: (m: Member) => teamApi.approve(m.id),
    onSuccess: async () => {
      await afterChange();
      toast.success("Promoter aprovado.", "As campanhas da equipe já estão disponíveis.");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const reject = useMutation({
    mutationFn: (m: Member) => teamApi.reject(m.id),
    onSuccess: async () => {
      await afterChange();
      setAction(null);
      toast.success("Solicitação recusada.");
    },
    onError: (e) => setActionError(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: (m: Member) => teamApi.remove(m.id),
    onSuccess: async () => {
      await afterChange();
      setAction(null);
      toast.success("Promoter removido da equipe.");
    },
    onError: (e) => setActionError(errorMessage(e)),
  });
  const rotate = useMutation({
    mutationFn: teamApi.rotateInvite,
    onSuccess: async (data) => {
      qc.setQueryData(keys.invite, data);
      setRotateOpen(false);
      toast.success("Novo código gerado.", "O código anterior deixou de funcionar.");
    },
    onError: (e) => setRotateError(errorMessage(e)),
  });

  const items = useMemo(() => {
    const list = members.data?.items ?? [];
    // pending first, keep server order otherwise
    return [...list].sort((a, b) => Number(b.status === "pending") - Number(a.status === "pending"));
  }, [members.data]);

  const closeAction = () => {
    setAction(null);
    setActionError(null);
  };
  const inviteUrl = safeUrl(invite.data?.invite_url);

  return (
    <>
      <PageHeader
        title="Equipe"
        description={
          approvedCount.data ? `${formatNumber(approvedCount.data.total)} ${approvedCount.data.total === 1 ? "promoter aprovado" : "promoters aprovados"}` : undefined
        }
      />

      <section aria-labelledby="invite-title" className="mb-8 rounded-card border border-line-subtle bg-surface-raised p-4 md:p-6">
        <h2 id="invite-title" className="mb-4 font-heading text-section">
          Convite da equipe
        </h2>
        {invite.isPending ? (
          <LoadingRegion className="flex flex-col gap-3">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-6 w-full max-w-md" />
          </LoadingRegion>
        ) : invite.isError ? (
          <ErrorState onRetry={() => invite.refetch()} retrying={invite.isFetching} />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-[auto_minmax(0,1fr)]">
              <div className="min-w-0">
                <p className="text-caption text-ink-muted">Código</p>
                <p className="text-section font-bold tracking-[0.08em] tabular-nums [overflow-wrap:anywhere]">{invite.data.invite_code}</p>
              </div>
              <div className="min-w-0">
                <p className="text-caption text-ink-muted">Link</p>
                <p className="text-label font-normal text-ink-secondary [overflow-wrap:anywhere]">{invite.data.invite_url}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <CopyButton
                text={inviteUrl ?? invite.data.invite_url}
                label="Copiar link"
                successMessage="Link de convite copiado."
                variant="secondary"
                size="md"
              />
              <CopyButton text={invite.data.invite_code} label="Copiar código" successMessage="Código copiado." />
              <Button variant="ghost" icon={RotateCw} onClick={() => setRotateOpen(true)}>
                Gerar novo código
              </Button>
            </div>
            <p className="flex items-start gap-2 text-caption text-ink-muted">
              <Link2 aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0" />
              Quem entra pelo convite fica Pendente até você aprovar.
            </p>
          </div>
        )}
      </section>

      <div className="mb-6 flex flex-col gap-4">
        <TextField
          label="Buscar por nome ou @"
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
          options={FILTERS}
          value={filter}
          onChange={(v) => {
            setFilter(v);
            setOffset(0);
          }}
        />
      </div>

      {members.isPending ? (
        <LoadingRegion className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </LoadingRegion>
      ) : members.isError && !members.data ? (
        <Card>
          <ErrorState onRetry={() => members.refetch()} retrying={members.isFetching} />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          {debounced ? (
            <EmptyState icon={UserRoundSearch} title="Nenhum promoter encontrado" description="Tente outro nome ou @." />
          ) : (
            <EmptyState
              icon={Users}
              title="Sua equipe ainda está vazia"
              description="Compartilhe o link ou o código de convite para os promoters pedirem entrada."
            />
          )}
        </Card>
      ) : (
        <>
          {/* md+: table */}
          <div className="hidden md:block" aria-busy={members.isFetching}>
            <table className="w-full border-collapse overflow-hidden rounded-card border border-line-subtle text-left">
              <caption className="sr-only">Promoters da equipe</caption>
              <thead className="bg-surface-raised text-label text-ink-secondary">
                <tr>
                  <th scope="col" className="min-h-11 px-4 py-3 font-semibold">Promoter</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Instagram</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Status</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">Saldo</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Entrada</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Ações</th>
                </tr>
              </thead>
              <tbody className="bg-surface">
                {items.map((m) => (
                  <tr key={m.id} className="border-t border-line-subtle align-middle">
                    <td className="min-w-0 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar name={m.promoter.name} />
                        <div className="min-w-0">
                          <p className="text-label text-ink [overflow-wrap:anywhere]">{m.promoter.name}</p>
                          <p className="text-caption text-ink-muted [overflow-wrap:anywhere]">{m.promoter.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-label font-normal [overflow-wrap:anywhere]">@{m.promoter.instagram_username}</td>
                    <td className="px-4 py-3">
                      <StatusBadge kind={m.status} />
                    </td>
                    <td className="px-4 py-3 text-right text-label tabular-nums">
                      {m.status === "pending" ? <span className="text-ink-muted">Aguardando aprovação</span> : formatPoints(m.points_balance)}
                    </td>
                    <td className="px-4 py-3 text-label font-normal tabular-nums">{formatDate(m.joined_at)}</td>
                    <td className="px-4 py-3">
                      <MemberActions m={m} approve={approve} onAction={(kind) => setAction({ kind, member: m })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* <md: cards */}
          <ul className="flex flex-col gap-3 md:hidden" aria-busy={members.isFetching}>
            {items.map((m) => (
              <li key={m.id} className="min-w-0 rounded-card border border-line-subtle bg-surface p-4">
                <div className="flex items-start gap-3">
                  <Avatar name={m.promoter.name} />
                  <div className="min-w-0 flex-1">
                    <p className="text-body font-bold [overflow-wrap:anywhere]">{m.promoter.name}</p>
                    <p className="text-label font-normal text-ink-secondary [overflow-wrap:anywhere]">@{m.promoter.instagram_username}</p>
                  </div>
                  <StatusBadge kind={m.status} />
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <dt className="text-caption text-ink-muted">Saldo</dt>
                    <dd className="text-label tabular-nums">{m.status === "pending" ? "Aguardando aprovação" : formatPoints(m.points_balance)}</dd>
                  </div>
                  <div>
                    <dt className="text-caption text-ink-muted">Entrada</dt>
                    <dd className="text-label tabular-nums">{formatDate(m.joined_at)}</dd>
                  </div>
                </dl>
                <div className="mt-3 border-t border-line-subtle pt-3">
                  <MemberActions m={m} approve={approve} onAction={(kind) => setAction({ kind, member: m })} />
                </div>
              </li>
            ))}
          </ul>
          {members.data && (
            <Pagination total={members.data.total} limit={PAGE} offset={offset} onChange={setOffset} busy={members.isFetching && members.isPlaceholderData} />
          )}
        </>
      )}

      <ConfirmDialog
        open={action?.kind === "reject"}
        onClose={closeAction}
        onConfirm={() => action && reject.mutate(action.member)}
        title="Recusar solicitação"
        description={`Recusar a entrada de ${action?.member.promoter.name ?? ""}? A conta do promoter não é removida da plataforma.`}
        confirmLabel="Recusar"
        loadingLabel="Recusando…"
        variant="danger"
        loading={reject.isPending}
        error={actionError}
      />
      <ConfirmDialog
        open={action?.kind === "remove"}
        onClose={closeAction}
        onConfirm={() => action && remove.mutate(action.member)}
        title="Remover da equipe"
        description={`Remover ${action?.member.promoter.name ?? ""} da equipe? O histórico de pontos é mantido, mas ele deixa de participar das campanhas.`}
        confirmLabel="Remover"
        loadingLabel="Removendo…"
        variant="danger"
        loading={remove.isPending}
        error={actionError}
      />
      <ConfirmDialog
        open={rotateOpen}
        onClose={() => {
          setRotateOpen(false);
          setRotateError(null);
        }}
        onConfirm={() => {
          setRotateError(null);
          rotate.mutate();
        }}
        title="Gerar novo código"
        description="O código e o link atuais deixam de funcionar. Quem já está na equipe não é afetado."
        confirmLabel="Gerar novo código"
        loadingLabel="Gerando…"
        variant="danger"
        loading={rotate.isPending}
        error={rotateError}
      />
      <Dialog open={action?.kind === "adjust"} onClose={closeAction} title="Ajustar pontos" description={action ? `Saldo atual de ${action.member.promoter.name}: ${formatPoints(action.member.points_balance)}.` : undefined}>
        {action?.kind === "adjust" && <AdjustForm member={action.member} onClose={closeAction} onDone={afterChange} />}
      </Dialog>
    </>
  );
}

function MemberActions({
  m,
  approve,
  onAction,
}: {
  m: Member;
  approve: { mutate: (m: Member) => void; isPending: boolean; variables?: Member };
  onAction: (k: "reject" | "remove" | "adjust") => void;
}) {
  const busy = approve.isPending && approve.variables?.id === m.id;
  return (
    <div className="flex flex-wrap gap-2">
      {m.status === "pending" && (
        <>
          <Button size="sm" loading={busy} onClick={() => approve.mutate(m)}>
            {busy ? "Aprovando…" : "Aprovar"}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onAction("reject")}>
            Recusar
          </Button>
        </>
      )}
      {m.status === "approved" && (
        <>
          <Button size="sm" variant="secondary" onClick={() => onAction("adjust")}>
            Ajustar pontos
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onAction("remove")}>
            Remover
          </Button>
        </>
      )}
    </div>
  );
}

const adjustSchema = z.object({
  amount: z.string().refine((v) => {
    const n = parseIntStrict(v);
    return Number.isInteger(n) && n !== 0 && Math.abs(n) <= 1_000_000;
  }, "Informe um número inteiro diferente de zero. Use sinal negativo para remover pontos."),
  reason: z.string().trim().min(3, "O motivo precisa ter de 3 a 200 caracteres.").max(200, "O motivo precisa ter de 3 a 200 caracteres."),
});
type AdjustValues = z.infer<typeof adjustSchema>;

function AdjustForm({ member, onClose, onDone }: { member: Member; onClose: () => void; onDone: () => Promise<void> }) {
  const toast = useToast();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<AdjustValues>({ resolver: zodResolver(adjustSchema), defaultValues: { amount: "", reason: "" }, mode: "onBlur" });
  useDialogDirty(form.formState.isDirty);
  const m = useMutation({
    mutationFn: (v: AdjustValues) => teamApi.adjustPoints(member.id, { amount: parseIntStrict(v.amount), reason: v.reason.trim() }),
    onSuccess: async (updated) => {
      await onDone();
      onClose();
      toast.success("Pontos ajustados.", `Novo saldo de ${updated.promoter.name}: ${formatPoints(updated.points_balance)}.`);
    },
    onError: (e) => setFormError(applyServerError(e, form.setError, ["amount", "reason"])),
  });
  const e = form.formState.errors;
  return (
    <form
      noValidate
      onSubmit={form.handleSubmit((v) => {
        setFormError(null);
        m.mutate(v);
      })}
      className="flex flex-col gap-4"
    >
      <FormError message={formError} />
      <TextField
        label="Quantidade de pontos"
        type="number"
        inputMode="numeric"
        data-autofocus=""
        hint="Positivo adiciona, negativo remove (por exemplo, -50)."
        error={e.amount?.message}
        {...form.register("amount")}
      />
      <TextField label="Motivo" hint="Fica registrado no extrato do promoter." error={e.reason?.message} {...form.register("reason")} />
      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={m.isPending}>
          {m.isPending ? "Salvando…" : "Ajustar pontos"}
        </Button>
      </DialogActions>
    </form>
  );
}
