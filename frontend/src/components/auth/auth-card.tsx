"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { Brand } from "@/components/layout/parts";
import { cn } from "@/lib/cn";
import { safeNext } from "@/lib/safe-url";
import { homeFor, useAuth } from "./auth-provider";

/** Logged-in users opening /entrar or /cadastro are sent to their home (or a safe `next`). */
export function useRedirectIfAuthed(next?: string | null) {
  const { user, status } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(safeNext(next, homeFor(user)));
    }
  }, [status, user, next, router]);
}

/**
 * O cartão das telas de entrada (design system do Camarim, tela Entrar): vidro
 * espesso sobre a luz de palco, a marca no alto e a frase de abertura em
 * Instrument Serif — a serifada é a voz da PORTA, nunca do app. O trecho em
 * `highlight` acende em itálico lima.
 */
export function AuthCard({
  title,
  highlight,
  description,
  children,
  footer,
  width = "auth",
  eyebrow,
}: {
  title: string;
  highlight?: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: "auth" | "form";
  eyebrow?: ReactNode;
}) {
  return (
    <div className={cn("mx-auto w-full px-4 py-10 md:py-16", width === "auth" ? "max-w-auth" : "max-w-form")}>
      <div className="cartao-de-entrada flex flex-col gap-5 px-6 pb-8 pt-9 sm:px-10">
        <Brand withIcon />
        <div className="flex flex-col gap-2.5">
          {eyebrow && <div className="rotulo">{eyebrow}</div>}
          <h1 tabIndex={-1} className="titulo-de-entrada text-ink-strong outline-none">
            {title}
            {highlight && (
              <>
                {" "}
                <em className="italic text-success">{highlight}</em>
              </>
            )}
          </h1>
          {description && <p className="text-body text-ink-secondary">{description}</p>}
        </div>
        <div>{children}</div>
      </div>
      {footer && <div className="mt-6 text-center text-label font-normal text-ink-secondary">{footer}</div>}
    </div>
  );
}
