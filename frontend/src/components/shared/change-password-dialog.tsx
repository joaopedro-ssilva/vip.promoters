"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { FormError, PasswordField } from "@/components/ui/fields";
import { DialogActions } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { authApi } from "@/lib/api/auth";
import { applyServerError } from "@/lib/form";
import { passwordSchema } from "@/lib/validation";

const schema = z.object({
  current_password: z.string().min(1, "Informe sua senha atual."),
  new_password: passwordSchema,
});
type Values = z.infer<typeof schema>;

export function ChangePasswordDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose} title="Alterar senha" description="Por segurança, suas outras sessões serão encerradas.">
      <ChangePasswordForm onClose={onClose} />
    </Dialog>
  );
}

function ChangePasswordForm({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: "", new_password: "" },
    mode: "onBlur",
  });
  const m = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      onClose();
      toast.success("Senha alterada.");
    },
    onError: (e) => setFormError(applyServerError(e, form.setError, ["current_password", "new_password"])),
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
        label="Senha atual"
        autoComplete="current-password"
        data-autofocus=""
        error={e.current_password?.message}
        {...form.register("current_password")}
      />
      <PasswordField
        label="Nova senha"
        autoComplete="new-password"
        hint="Mínimo de 8 caracteres, com pelo menos uma letra e um número."
        error={e.new_password?.message}
        {...form.register("new_password")}
      />
      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={m.isPending}>
          {m.isPending ? "Salvando…" : "Alterar senha"}
        </Button>
      </DialogActions>
    </form>
  );
}
