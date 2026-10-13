"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useAuth } from "@/components/auth/auth-provider";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { ErrorState, Skeleton } from "@/components/ui/feedback";
import { FormError, TextField } from "@/components/ui/fields";
import { Avatar, Card, PageHeader } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { ChangePasswordDialog } from "@/components/shared/change-password-dialog";
import { DeleteAccountSection } from "@/components/shared/delete-account";
import { authApi } from "@/lib/api/auth";
import { errorMessage } from "@/lib/api/client";
import { promoterApi } from "@/lib/api/promoter";
import type { Membership } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { applyServerError } from "@/lib/form";
import { keys } from "@/lib/queries";
import { useTheme } from "@/lib/theme";
import { igUsernameSchema, nameSchema, normalizeIgUsername } from "@/lib/validation";
import { JoinTeamForm } from "./join-team";
import { useTeam } from "./team-provider";
import { VerificationPanel } from "./verification";

const schema = z.object({ name: nameSchema, instagram_username: igUsernameSchema });
type Values = z.infer<typeof schema>;

export function PromoterProfile() {
  const { logout } = useAuth();
  const [pw, setPw] = useState(false);
  const [theme, setTheme] = useTheme();
  const [leaving, setLeaving] = useState(false);

  return (
    <div className="mx-auto flex max-w-reading flex-col gap-8">
      <PageHeader title="Perfil" className="mb-0" />

      <ProfileForm />
      <Teams />

      <Card as="section" aria-labelledby="mais">
        <h2 id="mais" className="mb-4 font-heading text-section">
          Mais
        </h2>
        <div className="flex flex-col gap-4">
          <Link href="/promoter/extrato" className="inline-flex min-h-11 items-center text-label text-success underline">
            Extrato de pontos
          </Link>
          <fieldset>
            <legend className="mb-2 text-label">Tema</legend>
            <div className="flex flex-wrap gap-3">
              {(
                [
                  ["dark", "Escuro"],
                  ["light", "Claro"],
                ] as const
              ).map(([value, label]) => (
                <label key={value} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-control border border-line px-4 text-label hover:bg-surface-hover">
                  <input type="radio" name="tema" className="size-5" checked={theme === value} onChange={() => setTheme(value)} />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => setPw(true)}>
              Alterar senha
            </Button>
            <Button
              variant="secondary"
              icon={LogOut}
              loading={leaving}
              onClick={async () => {
                setLeaving(true);
                await logout();
              }}
            >
              {leaving ? "Saindo…" : "Sair da conta"}
            </Button>
          </div>
        </div>
      </Card>
      <DeleteAccountSection role="promoter" />
      <ChangePasswordDialog open={pw} onClose={() => setPw(false)} />
    </div>
  );
}

function ProfileForm() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<Values | null>(null);
  const currentIg = user?.promoter_profile?.instagram_username ?? "";

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: user?.name ?? "", instagram_username: currentIg },
    mode: "onBlur",
  });

  const save = useMutation({
    mutationFn: async (v: Values) => {
      let u = user!;
      if (v.name.trim() !== u.name) u = await authApi.updateMe({ name: v.name.trim() });
      const ig = normalizeIgUsername(v.instagram_username);
      if (ig !== u.promoter_profile?.instagram_username) u = await promoterApi.updateProfile({ instagram_username: ig });
      return u;
    },
    onSuccess: async (u) => {
      setUser(u);
      await qc.invalidateQueries({ queryKey: keys.memberships });
      form.reset({ name: u.name, instagram_username: u.promoter_profile?.instagram_username ?? "" });
      setConfirm(null);
      toast.success("Perfil atualizado.", u.promoter_profile?.verified ? undefined : "Se você mudou o @, suas equipes aguardam nova aprovação.");
    },
    onError: (e) => {
      setConfirm(null);
      setFormError(applyServerError(e, form.setError, ["name", "instagram_username"]));
    },
  });

  const submit = (v: Values) => {
    setFormError(null);
    if (normalizeIgUsername(v.instagram_username) !== currentIg) setConfirm(v);
    else save.mutate(v);
  };
  const e = form.formState.errors;

  return (
    <Card as="section" aria-labelledby="dados">
      <div className="mb-4 flex items-center gap-3">
        <Avatar name={user?.name} size="lg" />
        <h2 id="dados" className="min-w-0 font-heading text-section [overflow-wrap:anywhere]">
          {user?.name}
        </h2>
      </div>
      <form noValidate onSubmit={form.handleSubmit(submit)} className="flex flex-col gap-4">
        <FormError message={formError} />
        <TextField label="Nome" autoComplete="name" error={e.name?.message} {...form.register("name")} />
        <TextField
          label="Seu @ do Instagram"
          autoCapitalize="none"
          spellCheck={false}
          hint="Use o mesmo @ com que você participa das campanhas."
          error={e.instagram_username?.message}
          {...form.register("instagram_username")}
        />
        <TextField label="E-mail" value={user?.email ?? ""} readOnly hint="Somente leitura." />
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" loading={save.isPending && !confirm} disabled={!form.formState.isDirty}>
            {save.isPending && !confirm ? "Salvando…" : "Salvar perfil"}
          </Button>
        </div>
      </form>

      <div className="mt-6 border-t border-line-subtle pt-4">
        <VerificationPanel />
      </div>

      <ConfirmDialog
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        onConfirm={() => confirm && save.mutate(confirm)}
        title="Alterar o @ do Instagram?"
        description="Ao alterar o @, suas participações em equipes voltam para análise até o gestor aprovar de novo, e a verificação do @ precisa ser refeita. Seu saldo de pontos é mantido. Interações antigas feitas com outra conta não são transferidas automaticamente."
        confirmLabel="Alterar @"
        loadingLabel="Salvando…"
        loading={save.isPending}
      />
    </Card>
  );
}

function Teams() {
  const team = useTeam();
  const qc = useQueryClient();
  const toast = useToast();
  const [leaving, setLeaving] = useState<Membership | null>(null);
  const [error, setError] = useState<string | null>(null);

  const leave = useMutation({
    mutationFn: (m: Membership) => promoterApi.leave(m.id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: keys.memberships });
      qc.removeQueries({ queryKey: ["promoter"], predicate: (q) => q.queryKey[1] !== "memberships" });
      setLeaving(null);
      toast.success("Você saiu da equipe.");
    },
    onError: (e) => setError(errorMessage(e)),
  });

  return (
    <Card as="section" aria-labelledby="equipes">
      <h2 id="equipes" className="mb-4 font-heading text-section">
        Suas equipes
      </h2>
      {team.status === "loading" ? (
        <Skeleton className="h-20" />
      ) : team.status === "error" ? (
        <ErrorState onRetry={team.refetch} />
      ) : team.memberships.length === 0 ? (
        <p className="mb-4 text-label font-normal text-ink-secondary">Você ainda não está em nenhuma equipe.</p>
      ) : (
        <ul className="mb-6 flex flex-col gap-3">
          {team.memberships.map((m) => {
            const inUse = team.activeOrgId === m.organization.id;
            return (
              <li key={m.id} className="rounded-control bg-surface-raised p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-body font-bold [overflow-wrap:anywhere]">{m.organization.name}</p>
                    {m.organization.instagram_username && <p className="text-caption text-ink-muted">@{m.organization.instagram_username}</p>}
                    <p className="text-caption text-ink-muted tabular-nums">Desde {formatDate(m.joined_at)}</p>
                  </div>
                  <StatusBadge kind={m.status} />
                </div>
                {m.status === "pending" && <p className="mt-2 text-label font-normal text-ink-secondary">Sua entrada está em análise. Você poderá participar após a aprovação.</p>}
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {m.status === "approved" &&
                    (inUse ? (
                      <span className="text-label text-success">Equipe em uso</span>
                    ) : (
                      <Button size="sm" variant="secondary" onClick={() => team.setActiveOrg(m.organization.id)}>
                        Usar esta equipe
                      </Button>
                    ))}
                  {(m.status === "approved" || m.status === "pending") && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setError(null);
                        setLeaving(m);
                      }}
                    >
                      {m.status === "pending" ? "Cancelar solicitação" : "Sair da equipe"}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <h3 className="mb-3 font-sans text-body font-bold">Entrar em uma equipe</h3>
      <JoinTeamForm compact />

      <ConfirmDialog
        open={leaving !== null}
        onClose={() => setLeaving(null)}
        onConfirm={() => leaving && leave.mutate(leaving)}
        title={leaving?.status === "pending" ? "Cancelar solicitação" : "Sair da equipe"}
        description={`Sair da equipe ${leaving?.organization.name ?? ""}? Você deixa de ver as campanhas e a lojinha dela.`}
        confirmLabel={leaving?.status === "pending" ? "Cancelar solicitação" : "Sair da equipe"}
        loadingLabel="Saindo…"
        variant="danger"
        loading={leave.isPending}
        error={error}
      />
    </Card>
  );
}
