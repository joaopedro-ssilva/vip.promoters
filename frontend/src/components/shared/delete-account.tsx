"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { FormError, PasswordField, TextField } from "@/components/ui/fields";
import { Card, DialogActions } from "@/components/ui/misc";
import { authApi } from "@/lib/api/auth";
import type { User } from "@/lib/api/types";
import { applyServerError } from "@/lib/form";

const schema = z.object({
  password: z.string().min(1, "Informe sua senha."),
  confirmation: z.string().refine((v) => v.trim().toUpperCase() === "EXCLUIR", "Digite EXCLUIR."),
});
type Values = z.infer<typeof schema>;

const WHAT_GOES: Record<User["role"], string[]> = {
  manager: [
    "Sua organização, com equipe, campanhas, interações, lojinha e resgates.",
    "A conexão com o Instagram e as imagens enviadas.",
    "Seus promoters continuam com conta, mas saem da sua equipe.",
  ],
  promoter: [
    "Seu perfil, seu @ e sua participação em todas as equipes.",
    "Saldo, extrato e resgates (inclusive os pendentes).",
    "Seus comentários e menções ficam anônimos nas campanhas: os gestores veem o número, não você.",
  ],
};

/** Zona de perigo: exclusão definitiva da própria conta (LGPD). */
export function DeleteAccountSection({ role }: { role: User["role"] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card as="section" aria-labelledby="excluir-conta" className="border-danger-border">
      <h2 id="excluir-conta" className="mb-2 font-heading text-section">
        Excluir conta
      </h2>
      <p className="text-label text-ink-secondary">
        A exclusão é imediata e não pode ser desfeita. Sai junto:
      </p>
      <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-label text-ink-secondary">
        {WHAT_GOES[role].map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <Button variant="danger" icon={Trash2} className="mt-4" onClick={() => setOpen(true)}>
        Excluir minha conta
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        size="sm"
        title="Excluir sua conta?"
        description="Confirme com sua senha e digite EXCLUIR. Não há como recuperar depois."
      >
        <DeleteForm onClose={() => setOpen(false)} />
      </Dialog>
    </Card>
  );
}

function DeleteForm({ onClose }: { onClose: () => void }) {
  const { forgetSession } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirmation: "" },
    mode: "onBlur",
  });
  const m = useMutation({
    mutationFn: authApi.deleteAccount,
    onSuccess: () => forgetSession("/?conta=excluida"),
    onError: (e) => setFormError(applyServerError(e, form.setError, ["password", "confirmation"])),
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
      <PasswordField
        label="Sua senha"
        autoComplete="current-password"
        data-autofocus=""
        error={e.password?.message}
        {...form.register("password")}
      />
      <TextField
        label="Digite EXCLUIR para confirmar"
        autoComplete="off"
        autoCapitalize="characters"
        error={e.confirmation?.message}
        {...form.register("confirmation")}
      />
      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" variant="danger" loading={m.isPending}>
          {m.isPending ? "Excluindo…" : "Excluir definitivamente"}
        </Button>
      </DialogActions>
    </form>
  );
}
