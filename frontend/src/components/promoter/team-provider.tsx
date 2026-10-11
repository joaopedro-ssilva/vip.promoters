"use client";

import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import type { Membership } from "@/lib/api/types";
import { STORAGE_KEYS, useStoredValue } from "@/lib/local-store";
import { membershipsQuery } from "@/lib/queries";
import { JoinTeamCard, PendingTeamCard } from "./join-team";

interface TeamContextValue {
  status: "loading" | "error" | "ready";
  memberships: Membership[];
  approved: Membership[];
  pending: Membership[];
  /** approved membership currently in use (localStorage choice, else the first approved) */
  active: Membership | null;
  activeOrgId: string | null;
  setActiveOrg: (id: string) => void;
  refetch: () => void;
}

const TeamContext = createContext<TeamContextValue | null>(null);

export function TeamProvider({ children }: { children: ReactNode }) {
  const q = useQuery(membershipsQuery());
  const [stored, setStored] = useStoredValue(STORAGE_KEYS.activeOrg);

  const value = useMemo<TeamContextValue>(() => {
    const memberships = q.data ?? [];
    const approved = memberships.filter((m) => m.status === "approved");
    const pending = memberships.filter((m) => m.status === "pending");
    const active = approved.find((m) => m.organization.id === stored) ?? approved[0] ?? null;
    return {
      status: q.isPending ? "loading" : q.isError ? "error" : "ready",
      memberships,
      approved,
      pending,
      active,
      activeOrgId: active?.organization.id ?? null,
      setActiveOrg: (id: string) => setStored(id),
      refetch: () => void q.refetch(),
    };
  }, [q, stored, setStored]);

  return <TeamContext.Provider value={value}>{children}</TeamContext.Provider>;
}

export function useTeam(): TeamContextValue {
  const ctx = useContext(TeamContext);
  if (!ctx) throw new Error("useTeam must be used inside <TeamProvider>");
  return ctx;
}

/**
 * Renders `children(orgId, membership)` only when the promoter has an approved
 * team; otherwise the "join a team" form or the "pending approval" state.
 */
export function TeamGate({ children }: { children: (orgId: string, membership: Membership) => ReactNode }) {
  const team = useTeam();
  if (team.status === "loading") {
    return (
      <LoadingRegion className="flex flex-col gap-4">
        <Skeleton className="h-40" />
        <Skeleton className="h-32" />
      </LoadingRegion>
    );
  }
  if (team.status === "error") return <ErrorState onRetry={team.refetch} />;
  if (!team.active) {
    return team.pending.length > 0 ? <PendingTeamCard memberships={team.pending} /> : <JoinTeamCard />;
  }
  return <>{children(team.active.organization.id, team.active)}</>;
}
