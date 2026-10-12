"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api/auth";
import { ApiError, refreshSession, setUnauthorizedHandler } from "@/lib/api/client";
import type { User } from "@/lib/api/types";
import { safeNext } from "@/lib/safe-url";

export const ME_KEY = ["me"] as const;

export function homeFor(user: Pick<User, "role">): string {
  return user.role === "manager" ? "/gestor" : "/promoter";
}

function hasSessionCookie(): boolean {
  return document.cookie.split(";").some((c) => c.trim().startsWith("vip_session="));
}

async function fetchMe(): Promise<User | null> {
  // vip_session is a non-HttpOnly hint that a session may exist: skip the 401 round trip otherwise.
  if (!hasSessionCookie()) return null;
  try {
    return await authApi.me();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      // access token (15 min) probably expired: try the refresh token once
      if (await refreshSession()) {
        try {
          return await authApi.me();
        } catch (e2) {
          if (e2 instanceof ApiError && e2.status === 401) return null;
          throw e2;
        }
      }
      return null;
    }
    throw e;
  }
}

interface AuthContextValue {
  user: User | null;
  status: "loading" | "authenticated" | "anonymous" | "error";
  refetch: () => void;
  setUser: (u: User | null) => void;
  logout: () => Promise<void>;
  /** Clears local state after the account was deleted server side (no API call). */
  forgetSession: (to: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const router = useRouter();

  const q = useQuery({
    queryKey: ME_KEY,
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const resetClientState = useCallback(() => {
    qc.cancelQueries();
    qc.removeQueries({ predicate: (query) => query.queryKey[0] !== ME_KEY[0] });
    qc.setQueryData(ME_KEY, null);
  }, [qc]);

  useEffect(() => {
    let redirecting = false;
    setUnauthorizedHandler(() => {
      resetClientState();
      const path = window.location.pathname;
      if (redirecting || !/^\/(gestor|promoter)(\/|$)/.test(path)) return;
      redirecting = true;
      const next = safeNext(`${path}${window.location.search}`, "/");
      // full navigation on purpose: discards every piece of client state
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign(`/entrar?next=${encodeURIComponent(next)}`);
    });
    return () => setUnauthorizedHandler(null);
  }, [resetClientState]);

  const setUser = useCallback((u: User | null) => qc.setQueryData(ME_KEY, u), [qc]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* the cookies are cleared server side on a best-effort basis */
    }
    resetClientState();
    router.replace("/entrar");
  }, [resetClientState, router]);

  const forgetSession = useCallback(
    (to: string) => {
      resetClientState();
      router.replace(to);
    },
    [resetClientState, router],
  );

  const value = useMemo<AuthContextValue>(() => {
    const user = q.data ?? null;
    const status: AuthContextValue["status"] = q.isPending
      ? "loading"
      : q.isError
        ? "error"
        : user
          ? "authenticated"
          : "anonymous";
    return { user, status, refetch: () => void q.refetch(), setUser, logout, forgetSession };
  }, [q, setUser, logout, forgetSession]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
