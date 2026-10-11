"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Clock3, Users } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { FormError, TextField } from "@/components/ui/fields";
import { Card } from "@/components/ui/misc";
import { EmptyState } from "@/components/ui/feedback";
import { useToast } from "@/components/ui/toast";
import { promoterApi } from "@/lib/api/promoter";
import type { Membership } from "@/lib/api/types";
import { applyServerError } from "@/lib/form";
import { keys } from "@/lib/queries";
import { INVITE_MESSAGE, isValidInviteCode } from "@/lib/validation";
import { StatusBadge } from "@/components/ui/badge";

const schema = z.object({
  invite_code: z.string().trim().min(1, "Informe o código da equipe.").refine(isValidInviteCode, INVITE_MESSAGE),
});
type Values = z.infer<typeof schema>;

/** Form that sends POST /promoter/memberships. */
export function JoinTeamForm({ onJoined, compact }: { onJoined?: () => void; compact?: boolean }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { invite_code: "" }, mode: "onBlur" });

  const join = useMutation({
    mutationFn: (v: Values) => promoterApi.join(v.invite_code.trim().toUpperCase()),
    onSuccess: async (m) => {
      await qc.invalidateQueries({ queryKey: keys.memberships });
      form.reset();
      toast.success(
        m.status === "approved"
          ? `Você entrou na equipe ${m.organization.name}.`
          : "Solicitação enviada. Aguarde a aprovação do gestor.",
      );
      onJoined?.();
    },
    onError: (e) => setFormError(applyServerError(e, form.setError, ["invite_code"])),
  });

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit((v) => {
        setFormError(null);
        join.mutate(v);
      })}
      className="flex flex-col gap-4"
    >
      <FormError message={formError} />
      <TextField
        label="Código de convite"
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck={false}
        placeholder="Ex.: K7P2QD9M"
        hint={compact ? undefined : "O gestor da equipe fornece o código com 8 caracteres."}
        error={form.formState.errors.invite_code?.message}
        {...form.register("invite_code")}
      />
      <div>
        <Button type="submit" loading={join.isPending}>
          {join.isPending ? "Enviando…" : "Solicitar entrada"}
        </Button>
      </div>
    </form>
  );
}

export function JoinTeamCard() {
  return (
    <Card className="mx-auto max-w-reading">
      <div className="mb-4 flex items-center gap-3">
        <Users aria-hidden="true" strokeWidth={1.75} className="size-8 text-ink-muted" />
        <h2 className="font-heading text-section">Entre em uma equipe para começar</h2>
      </div>
      <p className="mb-6 text-body text-ink-secondary">
        Use o código de convite do seu gestor. Depois da aprovação, as campanhas, os pontos e a lojinha da equipe ficam disponíveis.
      </p>
      <JoinTeamForm />
    </Card>
  );
}

export function PendingTeamCard({ memberships }: { memberships: Membership[] }) {
  return (
    <Card className="mx-auto max-w-reading">
      <EmptyState
        align="start"
        icon={Clock3}
        title="Sua entrada está em análise"
        description="Você poderá participar após a aprovação."
        className="p-0"
      />
      <ul className="mt-4 flex flex-col gap-2">
        {memberships.map((m) => (
          <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-control bg-surface-raised p-3">
            <span className="min-w-0 text-label text-ink">{m.organization.name}</span>
            <StatusBadge kind="pending" />
          </li>
        ))}
      </ul>
      <p className="mt-4 text-label text-ink-secondary">
        Enquanto isso, você pode acessar o Perfil e sair da conta.
      </p>
    </Card>
  );
}
