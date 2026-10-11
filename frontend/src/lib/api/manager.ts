import { api } from "./client";
import type {
  Campaign,
  CampaignSource,
  InstagramAccount,
  InstagramMedia,
  Interaction,
  InteractionStatus,
  InteractionType,
  InviteInfo,
  LeaderboardEntry,
  LeaderboardPeriod,
  ManagerDashboard,
  Member,
  MembershipStatus,
  Organization,
  Paginated,
  Redemption,
  RedemptionStatus,
  Reward,
} from "./types";

export const dashboardApi = {
  manager: () => api.get<ManagerDashboard>("/dashboard/manager"),
};

export const organizationApi = {
  update: (body: { name?: string; auto_approve_promoters?: boolean }) =>
    api.patch<Organization>("/organization", body),
};

export const teamApi = {
  invite: () => api.get<InviteInfo>("/team/invite"),
  rotateInvite: () => api.post<InviteInfo>("/team/invite/rotate"),
  members: (q: { status?: MembershipStatus; search?: string; limit?: number; offset?: number }) =>
    api.get<Paginated<Member>>("/team/members", q),
  approve: (id: string) => api.post<Member>(`/team/members/${id}/approve`),
  reject: (id: string) => api.post<Member>(`/team/members/${id}/reject`),
  remove: (id: string) => api.post<Member>(`/team/members/${id}/remove`),
  adjustPoints: (id: string, body: { amount: number; reason: string }) =>
    api.post<Member>(`/team/members/${id}/adjust-points`, body),
  leaderboard: (q: { period?: LeaderboardPeriod; limit?: number }) =>
    api.get<{ items: LeaderboardEntry[] }>("/team/leaderboard", q),
};

export const instagramApi = {
  account: () =>
    api.get<{ account: InstagramAccount | null }>("/instagram/account").then((r) => r.account),
  connect: () => api.post<{ authorize_url: string }>("/instagram/connect"),
  disconnect: () => api.delete<void>("/instagram/account"),
  media: (q: { after?: string | null; limit?: number }) =>
    api.get<{ items: InstagramMedia[]; next_cursor: string | null }>("/instagram/media", q),
};

export interface CampaignCreateInput {
  title: string;
  description?: string;
  instructions?: string;
  source: CampaignSource;
  ig_media_id?: string;
  image_url?: string;
  caption?: string;
  starts_at?: string;
  ends_at?: string;
  points_comment: number;
  points_story_mention: number;
  max_story_mentions: number;
  dispatch?: boolean;
}

export interface CampaignUpdateInput {
  title?: string;
  description?: string;
  instructions?: string;
  ends_at?: string | null;
  points_comment?: number;
  points_story_mention?: number;
}

export const campaignsApi = {
  list: (q: { status?: string; limit?: number; offset?: number }) =>
    api.get<Paginated<Campaign>>("/campaigns", q),
  get: (id: string) => api.get<Campaign>(`/campaigns/${id}`),
  create: (body: CampaignCreateInput) => api.post<Campaign>("/campaigns", body),
  update: (id: string, body: CampaignUpdateInput) => api.patch<Campaign>(`/campaigns/${id}`, body),
  remove: (id: string) => api.delete<void>(`/campaigns/${id}`),
  dispatch: (id: string) => api.post<Campaign>(`/campaigns/${id}/dispatch`),
  end: (id: string) => api.post<Campaign>(`/campaigns/${id}/end`),
  sync: (id: string) =>
    api.post<{ fetched: number; new_interactions: number; awarded: number }>(
      `/campaigns/${id}/sync`,
    ),
  interactions: (
    id: string,
    q: { type?: InteractionType; status?: InteractionStatus; limit?: number; offset?: number },
  ) => api.get<Paginated<Interaction>>(`/campaigns/${id}/interactions`, q),
};

export const uploadsApi = {
  image: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.upload<{ url: string }>("/uploads/image", form);
  },
};

export interface RewardInput {
  name?: string;
  description?: string | null;
  image_url?: string | null;
  cost_points?: number;
  stock?: number | null;
  max_per_promoter?: number | null;
  is_active?: boolean;
}

export const rewardsApi = {
  list: (q: { include_inactive?: boolean; limit?: number; offset?: number } = {}) =>
    api.get<Paginated<Reward>>("/rewards", q),
  create: (body: RewardInput) => api.post<Reward>("/rewards", body),
  update: (id: string, body: RewardInput) => api.patch<Reward>(`/rewards/${id}`, body),
  remove: (id: string) => api.delete<void>(`/rewards/${id}`),
};

export const redemptionsApi = {
  list: (q: { status?: RedemptionStatus; search?: string; limit?: number; offset?: number }) =>
    api.get<Paginated<Redemption>>("/redemptions", q),
  fulfill: (id: string, note?: string) =>
    api.post<Redemption>(`/redemptions/${id}/fulfill`, note ? { note } : {}),
  cancel: (id: string, note?: string) =>
    api.post<Redemption>(`/redemptions/${id}/cancel`, note ? { note } : {}),
};

export const devApi = {
  simulateComment: (body: { campaign_id: string; username: string; text: string }) =>
    api.post<{ interaction: Interaction }>("/dev/simulate/comment", body),
  simulateStory: (body: { username: string }) =>
    api.post<{ interaction: Interaction }>("/dev/simulate/story-mention", body),
};
