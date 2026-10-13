import { api } from "./client";
import type {
  AppNotification,
  LeaderboardEntry,
  LeaderboardPeriod,
  Membership,
  OrganizationPreview,
  Paginated,
  PointTransaction,
  PromoterCampaign,
  PromoterCampaignDetail,
  PromoterHome,
  PromoterReward,
  Redemption,
  User,
  Verification,
} from "./types";

export const invitesApi = {
  preview: (code: string) => api.get<OrganizationPreview>(`/orgs/invite/${encodeURIComponent(code)}`),
};

export const promoterApi = {
  memberships: () =>
    api.get<{ items: Membership[] }>("/promoter/memberships").then((r) => r.items),
  join: (invite_code: string) => api.post<Membership>("/promoter/memberships", { invite_code }),
  leave: (id: string) => api.delete<void>(`/promoter/memberships/${id}`),
  updateProfile: (body: { instagram_username: string }) =>
    api.patch<{ user: User }>("/promoter/profile", body).then((r) => r.user),
  verification: () => api.get<Verification>("/promoter/verification"),
  startVerification: () => api.post<Verification>("/promoter/verification"),
  claimUsername: (instagram_username: string) =>
    api.post<Verification>("/promoter/username-claims", { instagram_username }),
  home: (orgId: string) => api.get<PromoterHome>("/promoter/home", { org_id: orgId }),
  campaigns: (orgId: string, status: "active" | "ended") =>
    api.get<Paginated<PromoterCampaign>>("/promoter/campaigns", {
      org_id: orgId,
      status,
      limit: 100,
    }),
  campaign: (id: string) => api.get<PromoterCampaignDetail>(`/promoter/campaigns/${id}`),
  leaderboard: (orgId: string, period: LeaderboardPeriod) =>
    api.get<{ items: LeaderboardEntry[]; me: { rank: number | null; points: number } | null }>(
      "/promoter/leaderboard",
      { org_id: orgId, period },
    ),
  rewards: (orgId: string) =>
    api.get<Paginated<PromoterReward>>("/promoter/rewards", { org_id: orgId, limit: 100 }),
  redeem: (id: string, request_id: string) =>
    api.post<Redemption>(`/promoter/rewards/${id}/redeem`, { request_id }),
  redemptions: (orgId: string, limit = 100, offset = 0) =>
    api.get<Paginated<Redemption>>("/promoter/redemptions", { org_id: orgId, limit, offset }),
  transactions: (orgId: string, limit: number, offset: number) =>
    api.get<Paginated<PointTransaction>>("/promoter/transactions", {
      org_id: orgId,
      limit,
      offset,
    }),
};

export const notificationsApi = {
  list: (limit = 20) =>
    api.get<{ items: AppNotification[]; unread_count: number }>("/notifications", { limit }),
  read: (id: string) => api.post<void>(`/notifications/${id}/read`),
  readAll: () => api.post<void>("/notifications/read-all"),
};
