"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Clock3, LinkIcon } from "lucide-react";
import { useState } from "react";
import { Button, ButtonLink } from "@/components/ui/button";
import { EmptyState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { FormError } from "@/components/ui/fields";
import { Avatar, CopyButton } from "@/components/ui/misc";
import { ApiError, errorMessage } from "@/lib/api/client";
import { invitesApi, promoterApi } from "@/lib/api/promoter";
import { keys, membershipsQuery } from "@/lib/queries";
import { homeFor, useAuth } from "./auth-provider";
import { AuthCard } from "./auth-card";

export function InviteView({ code }: { code: string }) {
  const { user, status, logout } = useAuth();
  const qc = useQueryClient();
  const normalized = code.trim().toUpperCase();
  const [joinError, setJoinError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const preview = useQuery({
    queryKey: ["invite", normalized],
    queryFn: () => invitesApi.preview(normalized),
    retry: false,
    staleTime: 60_000,
  });

  const isPromoter = status === "authenticated" && user?.role === "promoter";
  const memberships = useQuery({ ...membershipsQuery(), enabled: isPromoter });

  const join = useMutation({
    mutationFn: () => promoterApi.join(normalized),
    onSuccess: async () => {
      setSent(true);
      await qc.invalidateQueries({ queryKey: keys.memberships });
    },
    onError: (e) => setJoinError(errorMessage(e)),
  });

  if (preview.isPending || status === "loading") {
    return (
      <AuthCard title="Convite">
        <LoadingRegion className="flex flex-col gap-4">
          <Skeleton className="size-12 rounded-pill" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-12" />
        </LoadingRegion>
      </AuthCard>
    );
  }

  if (preview.isError) {
    const notFound = preview.error instanceof ApiError && (preview.error.status === 404 || preview.error.code === "invalid_invite");
    return (
      <AuthCard title="Convite">
        <EmptyState
          icon={LinkIcon}
          title={notFound ? "Este convite não está disponível" : "Não foi possível carregar o convite"}
          description={notFound ? "Peça um novo link ao gestor." : preview.error instanceof ApiError ? preview.error.message : undefined}
          action={
            notFound ? (
              <ButtonLink href={user ? homeFor(user) : "/"}>Ir para o início</ButtonLink>
            ) : (
              <Button variant="secondary" onClick={() => preview.refetch()}>
                Tentar novamente
              </Button>
            )
          }
        />
      </AuthCard>
    );
  }

  const org = preview.data;
  const mine = memberships.data?.find((m) => m.organization.id === org.id);

  let action: React.ReactNode;
  if (status !== "authenticated" || !user) {
    action = (
      <div className="flex flex-col gap-3">
        <ButtonLink href={`/cadastro?papel=promoter&convite=${encodeURIComponent(normalized)}`} block>
          Criar conta e solicitar entrada
        </ButtonLink>
        <ButtonLink href={`/entrar?convite=${encodeURIComponent(normalized)}&next=${encodeURIComponent(`/convite/${normalized}`)}`} variant="secondary" block>
          Já tenho conta
        </ButtonLink>
      </div>
    );
  } else if (user.role === "manager") {
    action = (
      <div className="flex flex-col gap-3">
        <p className="text-body text-ink-secondary">Este convite é para uma conta de promoter.</p>
        <Button variant="secondary" block onClick={() => void logout()}>
          Entrar com outra conta
        </Button>
      </div>
    );
  } else if (memberships.isPending) {
    action = <Skeleton className="h-12" />;
  } else if (mine?.status === "approved") {
    action = (
      <div className="flex flex-col gap-3">
        <p className="flex items-center gap-2 text-body text-success">
          <CircleCheck aria-hidden="true" strokeWidth={1.75} className="size-5 shrink-0" />
          Você já faz parte desta equipe
        </p>
        <ButtonLink href="/promoter" block>
          Abrir equipe
        </ButtonLink>
      </div>
    );
  } else if (mine?.status === "pending" || sent) {
    action = (
      <div role="status" className="flex items-start gap-3 rounded-control border border-warning bg-surface-raised p-4">
        <Clock3 aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-5 shrink-0 text-warning" />
        <div className="min-w-0">
          <p className="text-label text-warning">Pendente</p>
          <p className="text-body text-ink">Solicitação enviada. Aguarde a aprovação do gestor.</p>
        </div>
      </div>
    );
  } else {
    action = (
      <div className="flex flex-col gap-3">
        <FormError message={joinError} />
        <Button
          block
          loading={join.isPending}
          onClick={() => {
            setJoinError(null);
            join.mutate();
          }}
        >
          {join.isPending ? "Enviando…" : "Solicitar entrada"}
        </Button>
      </div>
    );
  }

  return (
    <AuthCard title="Entre para a equipe" highlight={org.name} eyebrow="Convite">
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <Avatar name={org.name} src={org.instagram_profile_picture_url} size="lg" />
          <div className="min-w-0">
            {org.instagram_username && <p className="text-label text-ink">@{org.instagram_username}</p>}
            <p className="text-caption text-ink-muted">
              {org.promoters_count} {org.promoters_count === 1 ? "promoter" : "promoters"} na equipe
            </p>
          </div>
        </div>
        <p className="text-body text-ink-secondary">
          Sua entrada precisa ser aprovada pelo gestor. Até lá, ela fica como Pendente e as campanhas da equipe não aparecem para você.
        </p>
        <div className="flex items-center justify-between gap-2 rounded-control bg-surface-raised p-3">
          <div className="min-w-0">
            <p className="text-caption text-ink-muted">Código da equipe</p>
            <p className="break-all text-body font-bold tracking-[0.08em] tabular-nums">{normalized}</p>
          </div>
          <CopyButton text={normalized} label="Copiar código" successMessage="Código copiado." iconOnly variant="ghost" />
        </div>
        {action}
      </div>
    </AuthCard>
  );
}
