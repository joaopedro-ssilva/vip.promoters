"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Check, Ticket, Users } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { FormError, PasswordField, TextField } from "@/components/ui/fields";
import { authApi } from "@/lib/api/auth";
import type { Role } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { applyServerError } from "@/lib/form";
import { safeNext } from "@/lib/safe-url";
import {
  emailSchema,
  igUsernameSchema,
  nameSchema,
  normalizeIgUsername,
  optionalInviteCodeSchema,
  passwordSchema,
} from "@/lib/validation";
import { homeFor, useAuth } from "./auth-provider";
import { AuthCard, useRedirectIfAuthed } from "./auth-card";

const base = z.object({
  name: nameSchema,
  email: emailSchema,
  password: passwordSchema,
  organization_name: z.string(),
  instagram_username: z.string(),
  invite_code: z.string(),
});
type Values = z.infer<typeof base>;

function schemaFor(role: Role) {
  return base.superRefine((v, ctx) => {
    if (role === "manager") {
      const r = nameSchema.safeParse(v.organization_name);
      if (!r.success) {
        ctx.addIssue({ code: "custom", path: ["organization_name"], message: "Informe o nome da organização (2 a 80 caracteres)." });
      }
    } else {
      const ig = igUsernameSchema.safeParse(v.instagram_username);
      if (!ig.success) {
        ctx.addIssue({ code: "custom", path: ["instagram_username"], message: "Informe um @ do Instagram válido." });
      }
      const code = optionalInviteCodeSchema.safeParse(v.invite_code);
      if (!code.success) {
        ctx.addIssue({ code: "custom", path: ["invite_code"], message: code.error.issues[0]?.message ?? "Código inválido." });
      }
    }
  });
}

const ROLES: { role: Role; title: string; text: string; icon: typeof Users }[] = [
  { role: "manager", title: "Sou gestor", text: "Organizo campanhas e recompensas", icon: Users },
  { role: "promoter", title: "Sou promoter", text: "Divulgo e troco pontos por benefícios", icon: Ticket },
];

function roleFromParam(p: string | null, hasInvite: boolean): Role | null {
  if (p === "gestor") return "manager";
  if (p === "promoter") return "promoter";
  return hasInvite ? "promoter" : null;
}

export function SignupFlow() {
  const params = useSearchParams();
  const convite = (params.get("convite") ?? "").trim().toUpperCase().slice(0, 16);
  const next = params.get("next");
  useRedirectIfAuthed(next);

  const initial = roleFromParam(params.get("papel"), convite !== "");
  const [role, setRole] = useState<Role | null>(initial);
  // an invite link already tells us the role: go straight to the details
  const [step, setStep] = useState<1 | 2>(convite && initial === "promoter" ? 2 : 1);

  if (step === 1 || !role) {
    return (
      <AuthCard
        width="form"
        eyebrow="Etapa 1 de 2"
        title="Como você vai usar o VIP Promoters?"
        footer={
          <p className="text-label text-ink-secondary">
            Já tem conta?{" "}
            <Link href="/entrar" className="text-accent underline">
              Entrar
            </Link>
          </p>
        }
      >
        <fieldset>
          <legend className="sr-only">Tipo de conta</legend>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {ROLES.map(({ role: r, title, text, icon: Icon }) => {
              const selected = role === r;
              return (
                <label
                  key={r}
                  className={cn(
                    "relative flex min-h-11 cursor-pointer flex-col gap-2 rounded-card border-2 bg-surface p-4 hover:bg-surface-hover has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-[3px] has-[:focus-visible]:outline-focus",
                    selected ? "border-accent" : "border-line",
                  )}
                >
                  <input
                    type="radio"
                    name="papel"
                    value={r}
                    checked={selected}
                    onChange={() => setRole(r)}
                    className="sr-only"
                  />
                  <Icon aria-hidden="true" strokeWidth={1.75} className="size-6 text-accent" />
                  <span className="text-body font-bold">{title}</span>
                  <span className="text-label font-normal text-ink-secondary">{text}</span>
                  {selected && (
                    <span className="inline-flex items-center gap-1 text-caption text-accent">
                      <Check aria-hidden="true" strokeWidth={1.75} className="size-4" />
                      Selecionado
                    </span>
                  )}
                </label>
              );
            })}
          </div>
        </fieldset>
        <div className="mt-6">
          <Button disabled={!role} onClick={() => setStep(2)} block className="sm:w-auto">
            Continuar
          </Button>
          {!role && <p className="mt-2 text-caption text-ink-muted">Escolha uma opção para continuar.</p>}
        </div>
      </AuthCard>
    );
  }

  return <DetailsStep role={role} convite={convite} next={next} onBack={() => setStep(1)} />;
}

function DetailsStep({ role, convite, next, onBack }: { role: Role; convite: string; next: string | null; onBack: () => void }) {
  const router = useRouter();
  const { setUser } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schemaFor(role)),
    defaultValues: { name: "", email: "", password: "", organization_name: "", instagram_username: "", invite_code: convite },
    mode: "onBlur",
  });
  const e = form.formState.errors;

  const register = useMutation({
    mutationFn: authApi.register,
    onSuccess: (user) => {
      setUser(user);
      const fallback = user.role === "manager" ? "/gestor" : convite ? "/promoter" : "/promoter/perfil";
      const dest = safeNext(next, fallback);
      // never send a promoter to /gestor (or vice versa): fall back to the role's home
      const ok = dest.startsWith(homeFor(user));
      router.replace(ok ? dest : fallback);
    },
    onError: (err) => {
      setFormError(
        applyServerError(err, form.setError, ["name", "email", "password", "organization_name", "instagram_username", "invite_code"]),
      );
    },
  });

  return (
    <AuthCard
      eyebrow="Etapa 2 de 2"
      title="Criar conta"
      description={role === "manager" ? "Conta de gestor" : "Conta de promoter"}
      footer={
        <p className="text-label text-ink-secondary">
          Já tem conta?{" "}
          <Link href="/entrar" className="text-accent underline">
            Entrar
          </Link>
        </p>
      }
    >
      <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={onBack} className="-ml-3 mb-4">
        Voltar
      </Button>
      <form
        noValidate
        onSubmit={form.handleSubmit((v) => {
          setFormError(null);
          register.mutate(
            role === "manager"
              ? { role, name: v.name.trim(), email: v.email.trim().toLowerCase(), password: v.password, organization_name: v.organization_name.trim() }
              : {
                  role,
                  name: v.name.trim(),
                  email: v.email.trim().toLowerCase(),
                  password: v.password,
                  instagram_username: normalizeIgUsername(v.instagram_username),
                  ...(v.invite_code.trim() ? { invite_code: v.invite_code.trim().toUpperCase() } : {}),
                },
          );
        })}
        className="flex flex-col gap-6"
      >
        <FormError message={formError} />
        <TextField label="Seu nome" autoComplete="name" error={e.name?.message} {...form.register("name")} />
        <TextField label="E-mail" type="email" autoComplete="email" inputMode="email" error={e.email?.message} {...form.register("email")} />
        <PasswordField
          label="Senha"
          autoComplete="new-password"
          hint="Mínimo de 8 caracteres, com pelo menos uma letra e um número."
          error={e.password?.message}
          {...form.register("password")}
        />
        {role === "manager" ? (
          <TextField
            label="Nome da organização"
            autoComplete="organization"
            error={e.organization_name?.message}
            {...form.register("organization_name")}
          />
        ) : (
          <>
            <TextField
              label="Seu @ do Instagram"
              autoComplete="off"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="@seuusuario"
              hint="Use o mesmo @ com que você participa das campanhas."
              error={e.instagram_username?.message}
              {...form.register("instagram_username")}
            />
            <TextField
              label="Código da equipe"
              optional
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              error={e.invite_code?.message}
              {...form.register("invite_code")}
            />
          </>
        )}
        <Button type="submit" block loading={register.isPending}>
          {register.isPending ? "Criando conta…" : "Criar conta"}
        </Button>
      </form>
    </AuthCard>
  );
}
