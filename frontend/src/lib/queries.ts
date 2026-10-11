import { queryOptions } from "@tanstack/react-query";
import { dashboardApi, instagramApi } from "./api/manager";
import { promoterApi } from "./api/promoter";

/** Query keys shared across screens (so mutations can invalidate precisely). */
export const keys = {
  dashboard: ["manager", "dashboard"] as const,
  campaigns: ["manager", "campaigns"] as const,
  campaign: (id: string) => ["manager", "campaign", id] as const,
  interactions: (id: string) => ["manager", "campaign", id, "interactions"] as const,
  members: ["manager", "members"] as const,
  invite: ["manager", "invite"] as const,
  leaderboard: ["manager", "leaderboard"] as const,
  rewards: ["manager", "rewards"] as const,
  redemptions: ["manager", "redemptions"] as const,
  igAccount: ["instagram", "account"] as const,
  igMedia: ["instagram", "media"] as const,
  memberships: ["promoter", "memberships"] as const,
  /** every promoter query is scoped by the active organisation */
  promoter: (orgId: string) => ["promoter", orgId] as const,
};

export const managerDashboardQuery = () =>
  queryOptions({
    queryKey: keys.dashboard,
    queryFn: dashboardApi.manager,
    staleTime: 30_000,
  });

export const igAccountQuery = () =>
  queryOptions({
    queryKey: keys.igAccount,
    queryFn: instagramApi.account,
    staleTime: 60_000,
  });

export const membershipsQuery = () =>
  queryOptions({
    queryKey: keys.memberships,
    queryFn: promoterApi.memberships,
    staleTime: 30_000,
  });
