"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { CheckboxField, FormError, TextField } from "@/components/ui/fields";
import { Card, PageHeader } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { ChangePasswordDialog } from "@/components/shared/change-password-dialog";
import { DeleteAccountSection } from "@/components/shared/delete-account";
import { authApi } from "@/lib/api/auth";
import { organizationApi } from "@/lib/api/manager";
import type { User } from "@/lib/api/types";
import { applyServerError } from "@/lib/form";
import { useTheme } from "@/lib/theme";
import { nameSchema } from "@/lib/validation";

const orgSchema = z.object({ name: nameSchema, auto: z.boolean() });
const meSchema = z.object({ name: nameSchema });

export function SettingsPage() {
  const { user, logout } = useAuth();
  const [pw, setPw] = useState(false);
  const [theme, setTheme] = useTheme();
  const [leaving, setLeaving] = useState(false);
  if (!user) return null;

  return (
    <div className="mx-auto flex max-w-form flex-col gap-8">
      <PageHeader title="Configurações" className="mb-0" />

      <OrgForm user={user} />
      <AccountForm user={user} onPassword={() => setPw(true)} />

      <Card as="section" aria-labelledby="aparencia">
        <h2 id="aparencia" className="mb-4 font-heading text-section">
          Aparência
        </h2>
        <fieldset>
          <legend className="sr-only">Tema</legend>
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
      </Card>

      <Card as="section" aria-labelledby="prefs">
        <h2 id="prefs" className="mb-2 font-heading text-section">
          Preferências
        </h2>
        <p className="text-label font-normal text-ink-secondary">Fuso horário: Horário de Brasília (fixo).</p>
        <p className="mt-4 text-label">
          A conexão com o Instagram fica em{" "}
          <Link href="/gestor/instagram" className="text-success underline">
            Instagram
          </Link>
          .
        </p>
      </Card>

      <div>
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

      <DeleteAccountSection role="manager" />

      <ChangePasswordDialog open={pw} onClose={() => setPw(false)} />
    </div>
  );
}

function OrgForm({ user }: { user: User }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const org = user.organization;
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof orgSchema>>({
    resolver: zodResolver(orgSchema),
    defaultValues: { name: org?.name ?? "", auto: org?.auto_approve_promoters ?? false },
    mode: "onBlur",
  });
  const m = useMutation({
    mutationFn: (v: z.infer<typeof orgSchema>) => organizationApi.update({ name: v.name.trim(), auto_approve_promoters: v.auto }),
    onSuccess: (updated) => {
      setUser({ ...user, organization: updated });
      form.reset({ name: updated.name, auto: updated.auto_approve_promoters });
      toast.success("Organização atualizada.");
    },
    onError: (e) => setFormError(applyServerError(e, form.setError, ["name"])),
  });

  return (
    <Card as="section" aria-labelledby="org">
      <h2 id="org" className="mb-4 font-heading text-section">
        Organização
      </h2>
      <form
        noValidate
        onSubmit={form.handleSubmit((v) => {
          setFormError(null);
          m.mutate(v);
        })}
        className="flex flex-col gap-4"
      >
        <FormError message={formError} />
        <TextField label="Nome da organização" error={form.formState.errors.name?.message} {...form.register("name")} />
        <CheckboxField
          label="Aprovar promoters automaticamente"
          hint="Quem entrar pelo convite já fica aprovado, sem passar pela fila."
          {...form.register("auto")}
        />
        <div>
          <Button type="submit" loading={m.isPending} disabled={!form.formState.isDirty}>
            {m.isPending ? "Salvando…" : "Salvar alterações"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function AccountForm({ user, onPassword }: { user: User; onPassword: () => void }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof meSchema>>({ resolver: zodResolver(meSchema), defaultValues: { name: user.name }, mode: "onBlur" });
  const m = useMutation({
    mutationFn: (v: z.infer<typeof meSchema>) => authApi.updateMe({ name: v.name.trim() }),
    onSuccess: (updated) => {
      setUser(updated);
      form.reset({ name: updated.name });
      toast.success("Dados da conta atualizados.");
    },
    onError: (e) => setFormError(applyServerError(e, form.setError, ["name"])),
  });
  return (
    <Card as="section" aria-labelledby="conta">
      <h2 id="conta" className="mb-4 font-heading text-section">
        Conta
      </h2>
      <form
        noValidate
        onSubmit={form.handleSubmit((v) => {
          setFormError(null);
          m.mutate(v);
        })}
        className="flex flex-col gap-4"
      >
        <FormError message={formError} />
        <TextField label="Seu nome" autoComplete="name" error={form.formState.errors.name?.message} {...form.register("name")} />
        <TextField label="E-mail" value={user.email} readOnly hint="Somente leitura." />
        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={m.isPending} disabled={!form.formState.isDirty}>
            {m.isPending ? "Salvando…" : "Salvar alterações"}
          </Button>
          <Button variant="secondary" onClick={onPassword}>
            Alterar senha
          </Button>
        </div>
      </form>
    </Card>
  );
}
