"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import type { Role } from "@/lib/api/types";
import { safeNext } from "@/lib/safe-url";
import { homeFor, useAuth } from "./auth-provider";

export function PageSkeleton() {
  return (
    <LoadingRegion className="mx-auto flex w-full max-w-workspace flex-col gap-6 px-4 py-8 md:px-6 lg:px-8">
      <Skeleton className="h-10 w-56" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <Skeleton className="h-64" />
    </LoadingRegion>
  );
}

/**
 * Client-side role gate (UX only; the backend enforces everything):
 * anonymous -> /entrar?next=..., wrong role -> that role's own home.
 */
export function RoleGuard({ role, children }: { role: Role; children: ReactNode }) {
  const { user, status, refetch } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") {
      const next = safeNext(`${pathname}${window.location.search}`, "/");
      router.replace(`/entrar?next=${encodeURIComponent(next)}`);
    } else if (status === "authenticated" && user && user.role !== role) {
      router.replace(homeFor(user));
    }
  }, [status, user, role, pathname, router]);

  if (status === "error") {
    return (
      <div className="mx-auto max-w-auth px-4 py-16">
        <ErrorState onRetry={refetch} message="Não foi possível verificar sua sessão agora. Tente novamente." />
      </div>
    );
  }
  if (status === "authenticated" && user?.role === role) return <>{children}</>;
  return <PageSkeleton />;
}
