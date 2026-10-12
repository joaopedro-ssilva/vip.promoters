"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { FormError, PasswordField, TextField } from "@/components/ui/fields";
import { authApi } from "@/lib/api/auth";
import { applyServerError } from "@/lib/form";
import { safeNext } from "@/lib/safe-url";
import { emailSchema } from "@/lib/validation";
import { homeFor, useAuth } from "./auth-provider";
import { AuthCard, useRedirectIfAuthed } from "./auth-card";

const schema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Informe sua senha."),
});
type Values = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { setUser } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const next = params.get("next");
  const convite = params.get("convite");

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
    mode: "onBlur",
  });

  const login = useMutation({
    mutationFn: authApi.login,
    onSuccess: (user) => {
      setUser(user);
      router.replace(safeNext(next, homeFor(user)));
    },
    onError: (e) => {
      const msg = applyServerError(e, form.setError, ["email", "password"]);
      setFormError(msg);
    },
  });

  useRedirectIfAuthed(next);

  const signupParams = new URLSearchParams();
  if (convite) signupParams.set("convite", convite);
  if (next && safeNext(next, "") ) signupParams.set("next", next);
  const signupHref = `/cadastro${signupParams.size ? `?${signupParams}` : ""}`;

  return (
    <AuthCard
      title="Bem-vindo"
      highlight="de volta."
      description="Acesse sua conta para acompanhar campanhas, pontos e resgates."
      footer={
        <p className="text-label text-ink-secondary">
          Ainda não tem conta?{" "}
          <Link href={signupHref} className="text-success underline">
            Criar conta
          </Link>
        </p>
      }
    >
      <form
        noValidate
        onSubmit={form.handleSubmit((v) => {
          setFormError(null);
          login.mutate({ email: v.email.trim().toLowerCase(), password: v.password });
        })}
        className="flex flex-col gap-6"
      >
        <FormError message={formError} />
        <TextField
          label="E-mail"
          type="email"
          autoComplete="email"
          inputMode="email"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
        <PasswordField
          label="Senha"
          autoComplete="current-password"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        <Button type="submit" size="md" block loading={login.isPending}>
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>
    </AuthCard>
  );
}
