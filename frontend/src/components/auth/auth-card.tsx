"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
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

export function AuthCard({
  title,
  description,
  children,
  footer,
  width = "auth",
  eyebrow,
}: {
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: "auth" | "form";
  eyebrow?: ReactNode;
}) {
  return (
    <div className={cn("mx-auto w-full px-4 py-12", width === "auth" ? "max-w-auth" : "max-w-form")}>
      <div className="rounded-panel border border-line-subtle bg-surface p-4 md:p-6">
        {eyebrow && <div className="mb-2 text-caption uppercase tracking-[0.08em] text-ink-muted">{eyebrow}</div>}
        <h1 tabIndex={-1} className="font-heading text-page outline-none">
          {title}
        </h1>
        {description && <p className="mt-2 text-body text-ink-secondary">{description}</p>}
        <div className="mt-6">{children}</div>
      </div>
      {footer && <div className="mt-6 text-center">{footer}</div>}
    </div>
  );
}
