/** TypeScript mirror of the shared objects in docs/ARCHITECTURE.md section 8. */

export type Role = "manager" | "promoter";

export interface Organization {
  id: string;
  name: string;
  invite_code: string;
  auto_approve_promoters: boolean;
  instagram_username: string | null;
  instagram_profile_picture_url: string | null;
}

export interface OrganizationPreview {
  id: string;
  name: string;
  instagram_username: string | null;
  instagram_profile_picture_url: string | null;
  promoters_count: number;
}

export interface PromoterProfile {
  /** null while the promoter is proving ownership of a disputed @ */
  instagram_username: string | null;
  verified: boolean;
  verification_method: "oauth" | "comment" | null;
}

/** @ ownership check: comment `code` on any post of an account connected to the app. */
export interface Verification {
  instagram_username: string | null;
  verified: boolean;
  claim_username: string | null;
  code: string | null;
  expires_at: string | null;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  created_at: string;
  organization: Organization | null;
  promoter_profile: PromoterProfile | null;
}

export type InstagramAccountStatus = "active" | "expired" | "revoked";

export interface InstagramAccount {
  ig_user_id: string;
  username: string;
  name: string | null;
  profile_picture_url: string | null;
  account_type: string | null;
  followers_count: number | null;
  status: InstagramAccountStatus;
  token_expires_at: string | null;
  webhook_subscribed: boolean;
  connected_at: string;
  scopes: string[];
}

export interface InstagramMedia {
  id: string;
  caption: string | null;
  media_type: string;
  media_product_type: string | null;
  media_url: string | null;
  thumbnail_url: string | null;
  permalink: string | null;
  timestamp: string;
  like_count: number | null;
  comments_count: number | null;
}

export type MembershipStatus = "pending" | "approved" | "rejected" | "removed";

export interface Member {
  id: string;
  status: MembershipStatus;
  points_balance: number;
  total_earned: number;
  joined_at: string;
  approved_at: string | null;
  promoter: {
    id: string;
    name: string;
    email: string;
    instagram_username: string | null;
    verified: boolean;
  };
}

export interface Membership {
  id: string;
  status: MembershipStatus;
  points_balance: number;
  total_earned: number;
  joined_at: string;
  organization: OrganizationPreview;
}

export type CampaignStatus = "draft" | "active" | "ended";
export type CampaignSource = "existing" | "publish";

export interface CampaignStats {
  comments_awarded: number;
  story_mentions_awarded: number;
  participants: number;
  points_issued: number;
  unmatched: number;
}

export interface Campaign {
  id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  status: CampaignStatus;
  source: CampaignSource;
  ig_media_id: string | null;
  permalink: string | null;
  media_type: string | null;
  media_url: string | null;
  thumbnail_url: string | null;
  caption: string | null;
  publish_image_url: string | null;
  starts_at: string | null;
  ends_at: string | null;
  points_comment: number;
  points_story_mention: number;
  max_story_mentions: number;
  dispatched_at: string | null;
  last_synced_at: string | null;
  created_at: string;
  stats: CampaignStats;
}

export type InteractionType = "comment" | "story_mention";
export type InteractionStatus = "awarded" | "duplicate" | "unmatched" | "out_of_window";

export interface Interaction {
  id: string;
  campaign_id: string | null;
  type: InteractionType;
  status: InteractionStatus;
  ig_username: string;
  text: string | null;
  media_url: string | null;
  occurred_at: string;
  points_awarded: number;
  promoter: { membership_id: string; name: string } | null;
}

export interface PromoterCampaign {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  status: CampaignStatus;
  permalink: string | null;
  media_type: string | null;
  media_url: string | null;
  thumbnail_url: string | null;
  caption: string | null;
  starts_at: string | null;
  ends_at: string | null;
  points_comment: number;
  points_story_mention: number;
  max_story_mentions: number;
  my: { comment_done: boolean; story_mentions_done: number; points_earned: number };
}

export interface PromoterCampaignDetail extends PromoterCampaign {
  my_interactions: Interaction[];
}

export interface Reward {
  id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  cost_points: number;
  stock: number | null;
  max_per_promoter: number | null;
  is_active: boolean;
  redeemed_count: number;
  created_at: string;
}

export interface PromoterReward extends Reward {
  can_afford: boolean;
  my_redemptions_count: number;
  available: boolean;
}

export type RedemptionStatus = "pending" | "fulfilled" | "cancelled";

export interface Redemption {
  id: string;
  code: string;
  status: RedemptionStatus;
  cost_points: number;
  note: string | null;
  created_at: string;
  resolved_at: string | null;
  reward: { id: string; name: string; image_url: string | null };
  promoter?: { membership_id: string; name: string; instagram_username: string | null } | null;
  organization_name?: string | null;
}

export type TransactionType = "earn" | "redeem" | "refund" | "adjust";

export interface PointTransaction {
  id: string;
  amount: number;
  type: TransactionType;
  description: string;
  balance_after: number;
  created_at: string;
}

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  membership_id: string;
  name: string;
  instagram_username: string | null;
  points: number;
}

export type LeaderboardPeriod = "7d" | "30d" | "all";

export interface Paginated<T> {
  items: T[];
  total: number;
}

export interface ManagerDashboard {
  instagram_connected: boolean;
  kpis: {
    promoters_approved: number;
    promoters_pending: number;
    campaigns_active: number;
    interactions_7d: number;
    points_issued_30d: number;
    redemptions_pending: number;
  };
  interactions_by_day: { date: string; comments: number; story_mentions: number }[];
  top_promoters: LeaderboardEntry[];
  recent_interactions: Interaction[];
}

export interface PromoterHome {
  membership: Membership;
  rank: number | null;
  promoters_count: number;
  active_campaigns: PromoterCampaign[];
  recent_transactions: PointTransaction[];
  affordable_rewards_count: number;
}

export interface AppConfig {
  app_name: string;
  mock_mode: boolean;
}

export interface InviteInfo {
  invite_code: string;
  invite_url: string;
}
