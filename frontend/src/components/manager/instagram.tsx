"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Camera, CircleCheck, TriangleAlert } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { Card, PageHeader, Pair } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { useConnectInstagram } from "@/components/shared/use-connect-instagram";
import { errorMessage } from "@/lib/api/client";
import { instagramApi } from "@/lib/api/manager";
import type { InstagramAccount } from "@/lib/api/types";
import { expiresWithinDays, formatDateTime, formatNumber } from "@/lib/format";
import { igAccountQuery, keys } from "@/lib/queries";

const SCOPE_LABELS: Record<string, string> = {
  instagram_business_basic: "Ler os dados básicos da conta",
  instagram_business_manage_comments: "Ler os comentários das publicações",
  instagram_business_manage_messages: "Receber menções em story",
  instagram_business_content_publish: "Publicar posts pela plataforma",
};

export const IG_REASONS: Record<string, string> = {
  denied: "A autorização foi cancelada ou negada na Meta.",
  invalid_state: "A sessão de conexão expirou. Tente conectar novamente.",
  exchange_failed: "A Meta não confirmou a autorização. Tente conectar novamente.",
  instagram_error: "O Instagram retornou um erro. Tente novamente em instantes.",
  username_mismatch: "A conta autorizada não corresponde ao @ informado.",
  already_connected: "Esta conta do Instagram já está conectada a outro usuário.",
};

export function InstagramPage() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const toast = useToast();
  const connect = useConnectInstagram();
  const account = useQuery(igAccountQuery());
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const returned = params.get("status");
  const reason = params.get("reason");

  // coming back from the Meta authorisation screen: refresh the connection state
  useEffect(() => {
    if (returned) void qc.invalidateQueries({ queryKey: keys.igAccount });
  }, [returned, qc]);

  const disconnect = useMutation({
    mutationFn: instagramApi.disconnect,
    onSuccess: async () => {
      qc.setQueryData(keys.igAccount, null);
      await qc.invalidateQueries({ queryKey: keys.dashboard });
      setConfirm(false);
      toast.success("Instagram desconectado.", "O histórico foi mantido.");
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const a = account.data;

  return (
    <div className="mx-auto max-w-form">
      <PageHeader title="Instagram" />

      {returned === "connected" && (
        <p role="status" className="mb-6 flex items-start gap-2 rounded-control border border-success bg-surface-raised p-3 text-label text-success">
          <CircleCheck aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0" />
          Instagram conectado com sucesso.
        </p>
      )}
      {returned === "error" && (
        <p role="alert" className="mb-6 flex items-start gap-2 rounded-control border border-danger bg-surface-raised p-3 text-label text-danger">
          <CircleAlert aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0" />
          <span className="min-w-0">
            Não foi possível conectar o Instagram.
            {reason ? ` ${IG_REASONS[reason] ?? "Tente novamente em instantes."}` : ""}
          </span>
        </p>
      )}

      <Card as="section" aria-labelledby="ig-card">
        <div className="mb-4 flex items-center gap-3">
          <Camera aria-hidden="true" strokeWidth={1.75} className="size-8 text-ink" />
          <h2 id="ig-card" className="font-heading text-section">
            Conexão
          </h2>
        </div>

        {account.isPending ? (
          <LoadingRegion className="flex flex-col gap-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-20" />
          </LoadingRegion>
        ) : account.isError ? (
          <ErrorState onRetry={() => account.refetch()} retrying={account.isFetching} />
        ) : !a ? (
          <div className="flex flex-col gap-4">
            <p className="text-body text-ink-secondary">Conecte sua conta profissional para selecionar publicações e verificar participações.</p>
            <p className="text-caption text-ink-muted">A autenticação acontece na Meta. Você nunca informa senha ou token por aqui.</p>
            <div>
              <Button size="lg" loading={connect.isPending} onClick={() => connect.mutate()} className="w-full sm:w-auto">
                {connect.isPending ? "Conectando…" : "Conectar Instagram"}
              </Button>
            </div>
          </div>
        ) : (
          <Connected a={a} connect={connect} />
        )}
      </Card>

      {a && (
        <div className="mt-6">
          <Button variant="ghost" onClick={() => { setError(null); setConfirm(true); }}>
            Desconectar
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        onConfirm={() => {
          setError(null);
          disconnect.mutate();
        }}
        title="Desconectar o Instagram"
        description="A verificação de comentários e menções fica pausada e não será possível publicar ou disparar campanhas. As campanhas, interações e pontos já registrados são mantidos."
        confirmLabel="Desconectar"
        loadingLabel="Desconectando…"
        variant="danger"
        loading={disconnect.isPending}
        error={error}
      />
    </div>
  );
}

function Connected({ a, connect }: { a: InstagramAccount; connect: ReturnType<typeof useConnectInstagram> }) {
  const needsReconnect = a.status !== "active";
  const expiresSoon = expiresWithinDays(a.token_expires_at, 10) && !needsReconnect;
  return (
    <div className="flex flex-col gap-6">
      {needsReconnect && (
        <div role="alert" className="flex flex-col gap-3 rounded-control border border-warning bg-surface-raised p-4">
          <p className="flex items-start gap-2 text-label text-warning">
            <TriangleAlert aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0" />
            <span className="min-w-0">
              {a.status === "expired" ? "A conexão expirou." : "A autorização foi revogada."} Reconecte o Instagram para retomar a verificação das participações.
            </span>
          </p>
          <div>
            <Button loading={connect.isPending} onClick={() => connect.mutate()}>
              {connect.isPending ? "Conectando…" : "Reconectar"}
            </Button>
          </div>
        </div>
      )}
      {expiresSoon && (
        <p className="rounded-control border border-warning bg-surface-raised p-3 text-label text-warning">
          A autorização expira em breve ({formatDateTime(a.token_expires_at)}). Ela é renovada automaticamente; se falhar, reconecte.
        </p>
      )}
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Pair label="Conta">@{a.username}</Pair>
        <Pair label="Tipo de conta">{a.account_type ?? "—"}</Pair>
        <Pair label="Situação">{a.status === "active" ? "Conectada" : a.status === "expired" ? "Expirada" : "Revogada"}</Pair>
        <Pair label="Seguidores">{a.followers_count !== null ? formatNumber(a.followers_count) : "—"}</Pair>
        <Pair label="Conectada em">{formatDateTime(a.connected_at)}</Pair>
        <Pair label="Autorização válida até">{formatDateTime(a.token_expires_at)}</Pair>
        <Pair label="Notificações em tempo real">
          {a.webhook_subscribed ? "Ativas" : "Não ativas (a plataforma consulta os comentários periodicamente)"}
        </Pair>
      </dl>
      <div>
        <h3 className="mb-2 text-label text-ink">Permissões concedidas</h3>
        {a.scopes.length === 0 ? (
          <p className="text-label font-normal text-ink-muted">Nenhuma informação de permissões disponível.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {a.scopes.map((s) => (
              <li key={s} className="flex items-start gap-2 text-label font-normal text-ink-secondary">
                <CircleCheck aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-4 shrink-0 text-success" />
                <span className="min-w-0">{SCOPE_LABELS[s] ?? s}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
