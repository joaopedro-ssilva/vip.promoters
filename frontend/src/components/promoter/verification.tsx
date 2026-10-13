"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, MessageCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { FormError, TextField } from "@/components/ui/fields";
import { CopyButton } from "@/components/ui/misc";
import { authApi } from "@/lib/api/auth";
import { errorMessage } from "@/lib/api/client";
import { promoterApi } from "@/lib/api/promoter";
import type { Verification } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { membershipsQuery } from "@/lib/queries";
import { normalizeIgUsername } from "@/lib/validation";

const KEY = ["promoter", "verification"] as const;

/**
 * Prova de posse do @: o promoter comenta um código em qualquer post de uma conta
 * conectada ao app, e o @ que a Meta entrega no comentário confirma quem é o dono.
 * Funciona com conta pessoal (o login do Instagram só aceita conta profissional).
 */
export function VerificationPanel() {
  const { setUser } = useAuth();
  const q = useQuery({
    queryKey: KEY,
    queryFn: promoterApi.verification,
    // enquanto há código aberto, confere de tempos em tempos se o comentário chegou
    refetchInterval: (query) => (query.state.data?.code ? 15_000 : false),
  });
  const verified = q.data?.verified ?? false;

  // quando a verificação conclui, atualiza o usuário (selo e @ no perfil)
  useEffect(() => {
    if (!q.data || q.data.code) return;
    let cancelled = false;
    authApi
      .me()
      .then((u) => !cancelled && setUser(u))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [q.data, setUser]);

  if (q.isPending) return null;
  const v = q.data;
  if (!v) return null;

  if (verified && !v.code) {
    return (
      <p className="flex items-center gap-2 text-label">
        <BadgeCheck aria-hidden="true" strokeWidth={1.75} className="size-5 text-success" />
        <span className="text-success">@{v.instagram_username} verificado pelo Instagram</span>
      </p>
    );
  }
  return v.code ? <PendingCode v={v} /> : <StartVerification v={v} />;
}

/** Writes a fresh verification state straight into the cache (no extra request). */
function useSetVerification() {
  const qc = useQueryClient();
  return (v: Verification) => qc.setQueryData(KEY, v);
}

function StartVerification({ v }: { v: Verification }) {
  const setVerification = useSetVerification();
  const [error, setError] = useState<string | null>(null);
  const start = useMutation({
    mutationFn: promoterApi.startVerification,
    onSuccess: setVerification,
    onError: (e) => setError(errorMessage(e)),
  });
  return (
    <div className="flex flex-col gap-2">
      <p className="text-label text-ink-secondary">
        {v.instagram_username ? "@ ainda não verificado." : "Você ainda não tem um @ confirmado."}
      </p>
      <p className="text-caption text-ink-muted">
        Verificar mostra ao gestor que o @ é mesmo seu e impede que outra pessoa o use. Você vai comentar um código
        num post do Instagram; não precisa informar senha nem conectar nada.
      </p>
      <FormError message={error} />
      {v.instagram_username && (
        <div>
          <Button variant="secondary" icon={MessageCircle} loading={start.isPending} onClick={() => start.mutate()}>
            {start.isPending ? "Gerando…" : "Verificar meu @"}
          </Button>
        </div>
      )}
      <ClaimForm />
    </div>
  );
}

function PendingCode({ v }: { v: Verification }) {
  const teams = useQuery(membershipsQuery());
  const handles = Array.from(
    new Set((teams.data ?? []).map((m) => m.organization.instagram_username).filter((h): h is string => !!h)),
  );
  return (
    <div className="vidro flex flex-col gap-3 rounded-card p-4">
      <p className="rotulo">Seu código de verificação</p>
      <div className="flex flex-wrap items-center gap-3">
        <p className="cifra text-page text-violet">{v.code}</p>
        <CopyButton text={v.code ?? ""} label="Copiar código" successMessage="Código copiado." />
      </div>
      <ol className="flex list-decimal flex-col gap-1 pl-5 text-label text-ink-secondary">
        <li>
          Entre no Instagram como <strong className="text-ink">@{v.claim_username}</strong>.
        </li>
        <li>
          Comente o código em qualquer post
          {handles.length ? ` de ${handles.map((h) => `@${h}`).join(", ")}` : " de uma equipe que usa o VIP Promoters"}.
          Esse comentário não vale pontos.
        </li>
        <li>A confirmação aparece aqui em instantes. Depois você pode apagar o comentário.</li>
      </ol>
      {v.expires_at && <p className="text-caption text-ink-muted">Vale até {formatDateTime(v.expires_at)}.</p>}
      <ClaimForm compact />
    </div>
  );
}

/** Disputa: alguém cadastrou o seu @ sem verificar. */
function ClaimForm({ compact }: { compact?: boolean }) {
  const setVerification = useSetVerification();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const claim = useMutation({
    mutationFn: (u: string) => promoterApi.claimUsername(u),
    onSuccess: (v) => {
      setOpen(false);
      setValue("");
      setVerification(v);
    },
    onError: (e) => setError(errorMessage(e)),
  });
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="w-fit text-caption text-ink-muted underline hover:text-ink">
        {compact ? "Verificar outro @" : "Alguém cadastrou o seu @? Reivindique"}
      </button>
    );
  }
  return (
    <form
      noValidate
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        claim.mutate(normalizeIgUsername(value));
      }}
    >
      <TextField
        label="Seu @ do Instagram"
        autoCapitalize="none"
        spellCheck={false}
        hint="Se outra pessoa cadastrou este @ sem verificar, ele passa para você quando o código chegar."
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <FormError message={error} />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="secondary" size="sm" loading={claim.isPending}>
          Gerar código
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
