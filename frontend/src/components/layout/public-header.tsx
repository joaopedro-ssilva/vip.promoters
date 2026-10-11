"use client";

import { useAuth, homeFor } from "@/components/auth/auth-provider";
import { ButtonLink } from "@/components/ui/button";
import { Brand, ThemeToggle } from "./parts";

export function PublicHeader() {
  const { user, status } = useAuth();
  return (
    <header className="border-b border-line-subtle bg-surface">
      <div className="mx-auto flex min-h-16 w-full max-w-site items-center justify-between gap-3 px-4 md:px-6 lg:px-8">
        <Brand />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          {status === "authenticated" && user ? (
            <ButtonLink href={homeFor(user)} size="sm">
              Abrir painel
            </ButtonLink>
          ) : (
            <>
              <ButtonLink href="/entrar" variant="ghost" size="sm">
                Entrar
              </ButtonLink>
              <ButtonLink href="/cadastro" size="sm" className="hidden sm:inline-flex">
                Criar conta
              </ButtonLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
