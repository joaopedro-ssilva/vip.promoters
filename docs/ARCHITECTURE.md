# VIP Promoters — Architecture & API contract

This document is the single source of truth shared by the backend and the frontend.
If the implementation has to deviate from it, update this file in the same change.

## 1. Product

Instagram promotion management. Two roles:

- **Manager (gestor)**: signs up, gets an organization (his team), connects his Instagram
  professional account through the Meta API, creates campaigns from an Instagram post
  (an existing one or a new one published through the API), dispatches them to his promoters,
  sees who commented on the post / mentioned the account in a story, approves promoters and
  runs a rewards shop ("lojinha").
- **Promoter**: signs up with his Instagram @username, joins a manager's team with an invite
  code, sees dispatched campaigns, comments on the post / mentions the account in a story,
  earns points (**at most 1 awarded comment per campaign**), and redeems points for rewards.

All user-facing text (UI and API error messages) is **Brazilian Portuguese**.

### What the Meta API can and cannot do

| Signal | Available? | How |
|---|---|---|
| Comment on the manager's post | Yes | `comments` webhook + `GET /{media-id}/comments` polling fallback |
| Story that @mentions the manager | Yes | Messaging webhook, attachment `type: "story_mention"` (sender is an Instagram-scoped ID) |
| Who liked a post | **No** | Only `like_count` is exposed |
| Who reposted / shared | **No** | Not exposed |

So points come from **comments** and **story mentions** only. Likes/reposts are out of scope.

## 2. Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (latest stable, App Router) + TypeScript + Tailwind CSS v4 + TanStack Query + react-hook-form + zod + lucide-react |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic v2, httpx |
| Data | PostgreSQL 17, Redis 7 (rate limiting, cache, job queue) |
| Worker | `arq` worker (same image as backend): comment polling, token refresh, campaign auto-end, webhook processing |
| Infra | Docker Compose. Only `frontend` (127.0.0.1:3000) and `backend` (127.0.0.1:8000) are published to the host; Postgres and Redis are internal only. In production an HTTPS reverse proxy sits in front of the frontend and must set `X-Forwarded-For` (Next.js forwards a client-supplied value unchanged) |

Repository layout:

```
compose.yaml            full stack (built images)
compose.dev.yaml        dev override (backend hot reload)
.env.example  .env      root env file (the .env is git-ignored)
backend/                FastAPI app, alembic, tests, Dockerfile
frontend/               Next.js app, Dockerfile (standalone output)
design/                 DESIGN.md + tokens.css (visual direction for the frontend)
docs/ARCHITECTURE.md    this file
docs/META.md            guide (pt-BR): connecting Instagram, Meta App Review, timelines
```

The browser only ever talks to the Next.js origin. Next rewrites `/api/:path*` to
`${BACKEND_INTERNAL_URL}/api/:path*` (`http://backend:8000` in compose, `http://localhost:8000`
in local dev). No CORS is needed and auth cookies are first-party.

## 3. Conventions

- Base path: `/api/v1`. JSON, `snake_case`. IDs are UUID strings. Datetimes are ISO 8601 UTC.
- Lists: `?limit=` (default 20, max 100) and `?offset=`; response `{"items": [...], "total": n}`.
- Errors — one envelope for everything, including validation errors:

```json
{ "error": { "code": "insufficient_points", "message": "Você não tem pontos suficientes.", "fields": { "email": "E-mail inválido." } } }
```

  `fields` is present only for `validation_error` (422). Status codes: 400 business rule,
  401 unauthenticated, 403 forbidden / CSRF, 404 not found (also used for resources of
  another organization — never leak existence), 409 conflict, 422 validation, 429 rate limit
  (with `Retry-After`).
- Stable error codes used by the UI: `invalid_credentials`, `email_taken`,
  `instagram_username_taken`, `unauthenticated`, `forbidden`, `csrf_failed`, `not_found`,
  `validation_error`, `rate_limited`, `invalid_invite`, `already_member`,
  `membership_not_approved`, `instagram_not_connected`, `instagram_error`,
  `campaign_not_editable`, `campaign_not_active`, `insufficient_points`, `out_of_stock`,
  `redeem_limit_reached`, `reward_unavailable`, `redemption_not_pending`, `upload_invalid`.

### Validation rules

| Field | Rule |
|---|---|
| `name`, `organization_name` | 2–80 chars, trimmed |
| `email` | valid, ≤ 254 chars, stored lowercased |
| `instagram_username` | input may come with a leading `@` and uppercase; normalized to lowercase without `@`; must match `^[a-z0-9._]{1,30}$` |
| `invite_code` | 8 chars, uppercase letters and digits without ambiguous ones (no `0 O 1 I L`); lookups are case-insensitive |
| campaign `title` | 3–120 chars |
| campaign `description`, `instructions` | ≤ 2000 chars; `caption` ≤ 2200 |
| `points_comment`, `points_story_mention` | integers 0–100000. **0 disables that action.** At least one must be > 0. Defaults: 10 and 25 |
| `max_story_mentions` | 1–10, default 1 |
| `starts_at`, `ends_at` | `ends_at` must be after `starts_at`; `starts_at` defaults to the dispatch moment |
| reward `name` | 2–120 chars; `description` ≤ 1000 |
| `cost_points` | 1–1000000 |
| `stock` | `null` (unlimited) or 0–100000 |
| `max_per_promoter` | `null` or 1–1000 |
| adjust-points `reason` | 3–200 chars |
| redemption `note` | ≤ 500 chars |
| `image_url` fields | absolute `https://` URL (or a URL under `APP_URL`), ≤ 2000 chars |

Leaderboards rank by the sum of `earn` transactions in the period (redeeming does not lower
the rank); ties are broken by who reached the score first, then by name. Only approved
members with at least one point in the period are listed.

## 4. Authentication & security

- Passwords: Argon2id. Minimum 8 chars with at least one letter and one digit; max 128.
- Session: cookies set by the backend.
  - `vip_access` — JWT HS256, 15 min, `HttpOnly`, `SameSite=Lax`, path `/`. It carries `sid`
    (the refresh-token family id). On logout, on refresh-reuse detection and, for every *other*
    session, on change-password, the family is marked revoked (Redis, TTL = access lifetime;
    Postgres is the fail-closed fallback) and the access token stops working immediately (401).
  - `vip_refresh` — opaque random token, 30 days, `HttpOnly`, `SameSite=Lax`, path `/api/v1/auth`.
    Stored hashed (SHA-256). Rotated on every refresh; reuse of a rotated token revokes the
    whole token family. Refresh, logout and family revocation are serialised per family
    (`pg_advisory_xact_lock`), so a successor token never lands in a revoked family.
  - `vip_session` — value `1`, **not** HttpOnly, path `/`, same lifetime as the refresh token.
    It carries no authority; it only lets the frontend route guard know a session may exist.
  - `Secure` flag is controlled by `COOKIE_SECURE` (false on http://localhost, true in production).
- CSRF: every non-GET request under `/api/v1` except `/webhooks/*` and `/meta/*` must send
  `X-Requested-With: XMLHttpRequest`; if an `Origin` header is present it must be in
  `ALLOWED_ORIGINS`. Otherwise 403 `csrf_failed`.
- Frontend behaviour: on a 401 from any endpoint other than `/auth/*`, call
  `POST /auth/refresh` once (de-duplicated across concurrent requests) and retry; if the
  refresh fails, clear client state and go to `/entrar`.
- Authorization: role checks (`manager` / `promoter`) plus ownership scoping on every query
  (organization id for managers, membership for promoters). Cross-tenant access returns 404.
- Rate limits (Redis, configurable, per IP and per account where it applies): login,
  register, refresh, invite lookup, redeem, campaign sync, uploads, simulate. If Redis is down an
  in-process limiter takes over (never fail-open). `X-Forwarded-For` is honoured only when the
  direct peer is in `TRUSTED_PROXY_CIDRS` (default: loopback + RFC 1918, i.e. the compose network).
- Request bodies are capped while being received (also chunked): 1 MB everywhere, ~9 MB for
  `POST /uploads/image`, otherwise 413 `payload_too_large`. Uploads without a valid session are
  rejected with 401 before any byte is read.
- Instagram access tokens are encrypted at rest (Fernet, `TOKEN_ENCRYPTION_KEY`) and never
  returned by the API or written to logs.
- Webhooks are authenticated with `X-Hub-Signature-256` (HMAC-SHA256 of the raw body with the
  Meta app secret, constant-time compare). They are acknowledged immediately and processed by
  the worker. Processing is idempotent. Before queueing, the payload is reduced to exactly what
  the pipeline needs (comment events; story-mention attachments with sender id, recipient id,
  timestamp, mid and URL) so private message content is never queued or logged;
  transient failures are retried by the worker (5 tries, increasing backoff).
- OAuth `state`: random value bound to the user, HMAC-signed, 10 min TTL, also kept in an
  HttpOnly cookie and compared at the callback.
- Uploads: images only, max 8 MB, decoded and re-encoded to JPEG with Pillow (drops metadata
  and any embedded payload), random file name, served with `X-Content-Type-Options: nosniff`.
- Security headers on every response; `/docs` and `/openapi.json` disabled when
  `ENVIRONMENT=production`; the app refuses to boot in production with default secrets or
  with `META_MOCK_MODE=true`.
- Containers run as a non-root user.

## 5. Data model

```
users(id, email UNIQUE lowercased, password_hash, name, role[manager|promoter], is_active, created_at)
refresh_tokens(id, user_id, family_id, token_hash UNIQUE, expires_at, revoked_at, created_at, user_agent)
organizations(id, owner_id UNIQUE -> users, name, invite_code UNIQUE, auto_approve_promoters, created_at)
instagram_accounts(id, user_id UNIQUE -> users, ig_user_id UNIQUE, username, name, profile_picture_url,
                   account_type, followers_count, access_token_enc, token_expires_at, scopes,
                   webhook_subscribed, status[active|expired|revoked], connected_at)
promoter_profiles(user_id PK -> users, instagram_username UNIQUE lowercased, ig_scoped_id,
                  verified, verified_at, verification_method[oauth|null])
memberships(id, organization_id, promoter_id -> users, status[pending|approved|rejected|removed],
            points_balance CHECK >= 0, total_earned, joined_at, approved_at,
            UNIQUE(organization_id, promoter_id))
campaigns(id, organization_id, title, description, instructions, status[draft|active|ended],
          source[existing|publish], ig_media_id, permalink, media_type, media_url, thumbnail_url,
          caption, publish_image_url, starts_at, ends_at, points_comment, points_story_mention,
          max_story_mentions, dispatched_at, last_synced_at, created_at)
interactions(id, organization_id, campaign_id NULL, membership_id NULL, type[comment|story_mention],
             ig_event_id, ig_username, ig_scoped_id, text, media_url, occurred_at,
             status[awarded|duplicate|unmatched|out_of_window], points_awarded, created_at,
             UNIQUE(type, ig_event_id),
             UNIQUE(campaign_id, membership_id) WHERE type='comment' AND status='awarded')
point_transactions(id, organization_id, membership_id, amount (signed), type[earn|redeem|refund|adjust],
                   description, balance_after, interaction_id NULL, redemption_id NULL,
                   created_by NULL, created_at)
rewards(id, organization_id, name, description, image_url, cost_points CHECK > 0,
        stock NULL(=unlimited) CHECK >= 0, max_per_promoter NULL, is_active, archived_at, created_at)
redemptions(id, organization_id, reward_id, membership_id, request_id, cost_points,
            status[pending|fulfilled|cancelled], code UNIQUE, note, created_at, resolved_at,
            resolved_by, UNIQUE(membership_id, request_id))
notifications(id, user_id, type, title, body, link, read_at, created_at)
```

Points are **per membership** (a promoter can belong to several teams; each team has its own
balance and shop). `point_transactions` is an append-only ledger; `memberships.points_balance`
is the cached balance, always changed in the same DB transaction as the ledger row while the
membership row is locked (`SELECT ... FOR UPDATE`).

## 6. Interaction pipeline (the core rule set)

Webhooks, the polling job and the dev simulator all feed the **same** function.

1. **Idempotency** — `(type, ig_event_id)` is unique (`ig_event_id` = comment id, or message
   `mid` for story mentions). Already seen → skip.
2. **Resolve the organization** from the webhook `entry.id` (the manager's `ig_user_id`).
   Unknown account → drop.
3. **Comments**: only top-level comments (no `parent_id`), never the manager's own comments.
   Find the campaign with that `ig_media_id` in this organization. No campaign → drop (not
   stored). Campaign not `active`, or `occurred_at` outside `[starts_at, ends_at]` →
   stored as `out_of_window`, 0 points.
4. **Story mentions**: resolve the sender username with the User Profile API
   (`GET /{IGSID}?fields=username`). Candidate campaigns = this organization's `active`
   campaigns inside their time window with `points_story_mention > 0`, newest dispatch first.
   Pick the first one where the promoter is still under `max_story_mentions`; if all are at
   the limit → `duplicate` on the newest; if there is no candidate → `out_of_window`
   with `campaign_id = NULL`. Only the story CDN URL is stored, never the media itself.
5. **Match the promoter**: an `approved` membership of this organization whose promoter has
   `ig_scoped_id == from.id` or `lower(instagram_username) == lower(from.username)`.
   No match → `unmatched` (kept, so the manager can see it and so it can be re-matched).
6. **Limits**: comment → if this membership already has an awarded comment on this campaign →
   `duplicate`, 0 points. Story mention → as in step 4.
7. **Award** (one transaction): lock the membership, insert the interaction as `awarded`,
   insert the ledger row, bump `points_balance` and `total_earned`, create a notification for
   the promoter. The partial unique index is the last line of defence against races.
8. **Eligibility is re-checked after the locks**: the membership must still be `approved`, and the
   campaign still `active` and inside its window (30 s tolerance before `starts_at`, for comments
   and story mentions); otherwise the interaction is stored as `unmatched` / `out_of_window`.
9. **The manager is the identity gate for an @username.** An `unmatched` interaction is
   re-processed (in batches until exhausted) **only when a manager manually approves a
   membership** (`memberships.approved_by` is set). Consequences, all intentional:
   - Changing the @username (`PATCH /promoter/profile`) resets `verified` and sends **every**
     `approved` membership of that promoter back to `pending` (balance and history untouched);
     each manager gets a `username_changed` notification ("X alterou o @ de a para b e precisa de
     nova aprovação"). Nothing is re-matched until a manager approves again.
   - Auto-approval (`auto_approve_promoters`, at register or join) **never re-matches
     retroactively**: an auto-approved member only earns from events that occur after he joined
     (`occurred_at >= joined_at`, 30 s tolerance). Only manually approved members may be credited
     with earlier interactions.
   - Story-mention username lookup: a transient failure retries the job (nothing stored); a
     definitive failure stores the interaction as `unmatched` keeping `ig_scoped_id`.

Polling fallback: every `SYNC_INTERVAL_SECONDS` (default 120) the worker lists the comments
of each active campaign page by page (newest first) and feeds new ones to the pipeline. Each run
has a page budget (`SYNC_PAGES_PER_RUN`); a cut-short run stores a continuation cursor on the
campaign and resumes from it; after one complete pass a run may stop at the first page made only of
known comments (the `comments` webhook requires
Meta advanced access, so polling is what works before App Review). The worker also ends
campaigns past `ends_at` and refreshes Instagram tokens that expire in less than 10 days.

## 7. Instagram integration

"Instagram API with Instagram Login" (`graph.instagram.com`, version from
`META_GRAPH_VERSION`).

- Scopes requested for managers: `instagram_business_basic`,
  `instagram_business_manage_comments`, `instagram_business_manage_messages`,
  `instagram_business_content_publish`. For promoters (optional verification of the
  @username, professional accounts only): `instagram_business_basic`.
- Authorize: `https://www.instagram.com/oauth/authorize`; code exchange:
  `POST https://api.instagram.com/oauth/access_token`; long-lived exchange:
  `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token`; refresh:
  `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token`.
- Redirect URI: `${APP_URL}/api/v1/instagram/callback` (goes through the Next proxy).
- After connecting a manager: `POST /{ig-user-id}/subscribed_apps?subscribed_fields=comments,messages`.
- Publishing: `POST /{ig-user-id}/media` (`image_url`, `caption`) → poll container status →
  `POST /{ig-user-id}/media_publish`. The image URL must be publicly reachable by Meta.
- All Graph calls go through one interface (`InstagramClient`) with two implementations:
  the real one (httpx, timeouts, retries with backoff on 5xx/429, typed errors) and a
  **mock** one selected by `META_MOCK_MODE=true`. Mock mode makes the whole product usable
  without a Meta app: fake OAuth screen, fake media list, publish, and simulated
  comments / story mentions.

## 8. API

Auth column: `—` public, `U` any logged user, `M` manager, `P` promoter.

### Shared objects

```jsonc
// User
{ "id": "uuid", "name": "Ana", "email": "ana@x.com", "role": "manager", "created_at": "...",
  "organization": { /* Organization, managers only, else null */ },
  "promoter_profile": { "instagram_username": "ana.promo", "verified": false, "verification_method": null } /* promoters only, else null */ }

// Organization
{ "id": "uuid", "name": "Clube X", "invite_code": "K7P2QD9M", "auto_approve_promoters": false,
  "instagram_username": "clubex", "instagram_profile_picture_url": "https://..." }

// OrganizationPreview (safe to show to anyone holding the invite code)
{ "id": "uuid", "name": "Clube X", "instagram_username": "clubex", "instagram_profile_picture_url": null, "promoters_count": 12 }

// InstagramAccount
{ "ig_user_id": "1784...", "username": "clubex", "name": "Clube X", "profile_picture_url": null,
  "account_type": "BUSINESS", "followers_count": 1200, "status": "active",
  "token_expires_at": "...", "webhook_subscribed": true, "connected_at": "...", "scopes": ["..."] }

// InstagramMedia
{ "id": "1790...", "caption": "...", "media_type": "IMAGE", "media_product_type": "FEED",
  "media_url": "https://...", "thumbnail_url": null, "permalink": "https://www.instagram.com/p/...",
  "timestamp": "...", "like_count": 10, "comments_count": 3 }

// Member (manager view of a membership)
{ "id": "uuid", "status": "pending", "points_balance": 0, "total_earned": 0, "joined_at": "...", "approved_at": null,
  "promoter": { "id": "uuid", "name": "Bia", "email": "bia@x.com", "instagram_username": "bia.promo", "verified": false } }

// Membership (promoter view)
{ "id": "uuid", "status": "approved", "points_balance": 120, "total_earned": 300, "joined_at": "...",
  "organization": { /* OrganizationPreview */ } }

// Campaign (manager view)
{ "id": "uuid", "title": "...", "description": "...", "instructions": "...", "status": "active",
  "source": "existing", "ig_media_id": "1790...", "permalink": "https://...", "media_type": "IMAGE",
  "media_url": "https://...", "thumbnail_url": null, "caption": "...", "publish_image_url": null,
  "starts_at": "...", "ends_at": null, "points_comment": 10, "points_story_mention": 20, "max_story_mentions": 1,
  "dispatched_at": "...", "last_synced_at": "...", "created_at": "...",
  "stats": { "comments_awarded": 4, "story_mentions_awarded": 2, "participants": 5, "points_issued": 80, "unmatched": 1 } }

// PromoterCampaign (promoter view; never exposes other promoters)
{ "id": "uuid", "organization_id": "uuid", "title": "...", "description": "...", "instructions": "...", "status": "active",
  "permalink": "https://...", "media_type": "IMAGE", "media_url": "https://...", "thumbnail_url": null, "caption": "...",
  "starts_at": "...", "ends_at": null, "points_comment": 10, "points_story_mention": 20, "max_story_mentions": 1,
  "my": { "comment_done": true, "story_mentions_done": 0, "points_earned": 10 } }

// Interaction
{ "id": "uuid", "campaign_id": "uuid", "type": "comment", "status": "awarded", "ig_username": "bia.promo",
  "text": "Bora!", "media_url": null, "occurred_at": "...", "points_awarded": 10,
  "promoter": { "membership_id": "uuid", "name": "Bia" } /* null when unmatched */ }

// Reward
{ "id": "uuid", "name": "Entrada VIP", "description": "...", "image_url": null, "cost_points": 100,
  "stock": 5, "max_per_promoter": 1, "is_active": true, "redeemed_count": 2, "created_at": "..." }
// promoter view adds: "can_afford": true, "my_redemptions_count": 0, "available": true

// Redemption
{ "id": "uuid", "code": "VIP-8K2F4Q", "status": "pending", "cost_points": 100, "note": null,
  "created_at": "...", "resolved_at": null,
  "reward": { "id": "uuid", "name": "Entrada VIP", "image_url": null },
  "promoter": { "membership_id": "uuid", "name": "Bia", "instagram_username": "bia.promo" }, /* manager view */
  "organization_name": "Clube X" /* promoter view */ }

// PointTransaction
{ "id": "uuid", "amount": 10, "type": "earn", "description": "Comentário na campanha Sexta VIP",
  "balance_after": 130, "created_at": "..." }

// Notification
{ "id": "uuid", "type": "campaign_dispatched", "title": "...", "body": "...", "link": "/promoter/campanhas/uuid",
  "read_at": null, "created_at": "..." }

// LeaderboardEntry
{ "rank": 1, "membership_id": "uuid", "name": "Bia", "instagram_username": "bia.promo", "points": 300 }
```

### Endpoints

| Method & path | Auth | Request | Response |
|---|---|---|---|
| `GET /config` | — | | `{ "app_name": "VIP Promoters", "mock_mode": true }` |
| `GET /health` | — | | `{ "status": "ok" }` |
| **Auth** | | | |
| `POST /auth/register` | — | `{ name, email, password, role, organization_name? (required for manager), instagram_username? (required for promoter), invite_code? (promoter, optional) }` | 201 `{ user }` + cookies |
| `POST /auth/login` | — | `{ email, password }` | `{ user }` + cookies |
| `POST /auth/refresh` | cookie | | `{ user }` + rotated cookies |
| `POST /auth/logout` | U | | 204, cookies cleared |
| `GET /auth/me` | U | | `{ user }` |
| `PATCH /auth/me` | U | `{ name }` | `{ user }` |
| `POST /auth/change-password` | U | `{ current_password, new_password }` | 204 (other sessions revoked) |
| **Organization / team** | | | |
| `PATCH /organization` | M | `{ name?, auto_approve_promoters? }` | Organization |
| `GET /team/invite` | M | | `{ invite_code, invite_url }` |
| `POST /team/invite/rotate` | M | | `{ invite_code, invite_url }` |
| `GET /team/members` | M | `?status=&search=&limit=&offset=` | list of Member |
| `POST /team/members/{id}/approve` | M | | Member |
| `POST /team/members/{id}/reject` | M | | Member |
| `POST /team/members/{id}/remove` | M | | Member |
| `POST /team/members/{id}/adjust-points` | M | `{ amount (non-zero int), reason }` | Member |
| `GET /team/leaderboard` | M | `?period=all\|30d\|7d&limit=` | `{ items: LeaderboardEntry[] }` |
| **Instagram** | | | |
| `GET /instagram/account` | U | | `{ account: InstagramAccount \| null }` |
| `POST /instagram/connect` | U | | `{ authorize_url }` (browser navigates to it) |
| `GET /instagram/callback` | U | `?code=&state=` or `?error=` | 302 to `/gestor/instagram?status=connected\|error&reason=` (manager) or `/promoter/perfil?status=...` (promoter) |
| `DELETE /instagram/account` | U | | 204 |
| `GET /instagram/media` | M | `?after=&limit=` | `{ items: InstagramMedia[], next_cursor }` |
| **Campaigns (manager)** | | | |
| `GET /campaigns` | M | `?status=&limit=&offset=` | list of Campaign |
| `POST /campaigns` | M | `{ title, description?, instructions?, source, ig_media_id? (source=existing), image_url?, caption? (source=publish), starts_at?, ends_at?, points_comment, points_story_mention, max_story_mentions, dispatch? }` | 201 Campaign |
| `GET /campaigns/{id}` | M | | Campaign |
| `PATCH /campaigns/{id}` | M | `{ title?, description?, instructions?, ends_at?, points_*? (draft only) }` | Campaign |
| `DELETE /campaigns/{id}` | M | draft only | 204 |
| `POST /campaigns/{id}/dispatch` | M | | Campaign — publishes to Instagram first when `source=publish`, sets `active`, notifies every approved promoter |
| `POST /campaigns/{id}/end` | M | | Campaign |
| `POST /campaigns/{id}/sync` | M | | `{ fetched, new_interactions, awarded }` |
| `GET /campaigns/{id}/interactions` | M | `?type=&status=&limit=&offset=` | list of Interaction |
| `POST /uploads/image` | M | multipart `file` | 201 `{ url }` |
| `GET /uploads/{filename}` | — | | the JPEG |
| **Rewards & redemptions (manager)** | | | |
| `GET /rewards` | M | `?include_inactive=` | list of Reward |
| `POST /rewards` | M | `{ name, description?, image_url?, cost_points, stock?, max_per_promoter?, is_active? }` | 201 Reward |
| `PATCH /rewards/{id}` | M | same fields, all optional | Reward |
| `DELETE /rewards/{id}` | M | | 204 (archived if it already has redemptions) |
| `GET /redemptions` | M | `?status=&search=&limit=&offset=` | list of Redemption |
| `POST /redemptions/{id}/fulfill` | M | `{ note? }` | Redemption |
| `POST /redemptions/{id}/cancel` | M | `{ note? }` | Redemption (points refunded, stock returned) |
| `GET /dashboard/manager` | M | | see below |
| **Promoter** | | | |
| `GET /orgs/invite/{code}` | — | | OrganizationPreview |
| `GET /promoter/memberships` | P | | `{ items: Membership[] }` |
| `POST /promoter/memberships` | P | `{ invite_code }` | 201 Membership |
| `DELETE /promoter/memberships/{id}` | P | | 204 |
| `PATCH /promoter/profile` | P | `{ instagram_username }` | `{ user }` |
| `GET /promoter/home` | P | `?org_id=` | see below |
| `GET /promoter/campaigns` | P | `?org_id=&status=active\|ended` | list of PromoterCampaign |
| `GET /promoter/campaigns/{id}` | P | | PromoterCampaign + `my_interactions: Interaction[]` |
| `GET /promoter/leaderboard` | P | `?org_id=&period=` | `{ items: LeaderboardEntry[], me: { rank, points } }` |
| `GET /promoter/rewards` | P | `?org_id=` | list of Reward (promoter view, active only) |
| `POST /promoter/rewards/{id}/redeem` | P | `{ request_id (client-generated UUID, makes the call idempotent) }` | 201 Redemption |
| `GET /promoter/redemptions` | P | `?org_id=&limit=&offset=` | list of Redemption |
| `GET /promoter/transactions` | P | `?org_id=&limit=&offset=` | list of PointTransaction |
| **Notifications** | | | |
| `GET /notifications` | U | `?limit=` | `{ items: Notification[], unread_count }` |
| `POST /notifications/{id}/read` | U | | 204 |
| `POST /notifications/read-all` | U | | 204 |
| **Meta callbacks** | | | |
| `GET /webhooks/instagram` | — | `hub.mode`, `hub.verify_token`, `hub.challenge` | the challenge as plain text |
| `POST /webhooks/instagram` | signature | Meta payload | 200 |
| `POST /meta/deauthorize` | signed_request | | 200 |
| `POST /meta/data-deletion` | signed_request | | `{ url, confirmation_code }` |
| **Dev simulator (only when `META_MOCK_MODE=true`)** | | | |
| `GET /dev/instagram/authorize` | — | `?state=&redirect_uri=` | 302 back to the callback with a fake code |
| `POST /dev/simulate/comment` | M | `{ campaign_id, username, text }` | `{ interaction }` |
| `POST /dev/simulate/story-mention` | M | `{ username }` | `{ interaction }` |

Promoter endpoints taking `org_id` require an `approved` membership in that organization,
otherwise 403 `membership_not_approved`.

```jsonc
// GET /dashboard/manager
{ "instagram_connected": true,
  "kpis": { "promoters_approved": 12, "promoters_pending": 2, "campaigns_active": 1,
            "interactions_7d": 40, "points_issued_30d": 900, "redemptions_pending": 3 },
  "interactions_by_day": [ { "date": "2026-10-01", "comments": 4, "story_mentions": 1 } ], // last 14 days, zero-filled
  "top_promoters": [ /* LeaderboardEntry, 5 */ ],
  "recent_interactions": [ /* Interaction, 8 */ ] }

// GET /promoter/home
{ "membership": { /* Membership */ }, "rank": 3, "promoters_count": 12,
  "active_campaigns": [ /* PromoterCampaign */ ],
  "recent_transactions": [ /* PointTransaction, 5 */ ],
  "affordable_rewards_count": 2 }
```

## 9. Frontend routes

| Route | Who | What |
|---|---|---|
| `/` | public | landing page |
| `/entrar`, `/cadastro` | public | login, sign-up (role picker; `?papel=gestor\|promoter`, `?convite=CODE`) |
| `/convite/[code]` | public | team preview + join (sends to sign-up when logged out) |
| `/gestor` | M | overview |
| `/gestor/campanhas`, `/gestor/campanhas/nova`, `/gestor/campanhas/[id]` | M | campaigns |
| `/gestor/equipe`, `/gestor/ranking` | M | team, leaderboard |
| `/gestor/lojinha`, `/gestor/resgates` | M | rewards CRUD, redemption queue |
| `/gestor/instagram`, `/gestor/configuracoes` | M | connection, settings |
| `/promoter` | P | home |
| `/promoter/campanhas`, `/promoter/campanhas/[id]` | P | campaigns |
| `/promoter/lojinha`, `/promoter/resgates`, `/promoter/extrato` | P | shop, my redemptions, points history |
| `/promoter/ranking`, `/promoter/perfil` | P | leaderboard, profile and teams |

## 10. Environment variables

```
ENVIRONMENT=development            # development | production
APP_URL=http://localhost:3000      # public URL of the frontend (used for redirects, invite links, upload URLs)
ALLOWED_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+asyncpg://vip:vip@db:5432/vip
REDIS_URL=redis://redis:6379/0
SECRET_KEY=                        # JWT + state signing
TOKEN_ENCRYPTION_KEY=              # Fernet key
COOKIE_SECURE=false
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=30
META_MOCK_MODE=true
META_APP_ID=
META_APP_SECRET=
META_GRAPH_VERSION=v25.0
META_WEBHOOK_VERIFY_TOKEN=
SYNC_INTERVAL_SECONDS=120
SEED_DEMO=true                     # seed demo data on first boot (development only)
BACKEND_INTERNAL_URL=http://backend:8000   # frontend only
```

## 11. Backend implementation notes (clarifications to this contract)

Additions made while implementing; nothing above was removed or renamed.

- `META_GRAPH_VERSION` default is **v25.0** (current stable Graph API version, released 2026-02-18).
- `instagram_error` is returned with **502**. Other codes that can appear besides the list in section 3:
  `invalid_state` (400, e.g. rejecting a member that is not pending), `method_not_allowed` (405),
  `internal_error` (500), `payload_too_large` (413), `unavailable` (503, webhook queue down),
  `bad_request` (400, invalid webhook JSON), `conflict` (409), `unsupported_media_type` (415).
- `GET /orgs/invite/{code}` with an unknown code answers **404** with code `invalid_invite`
  (`POST /promoter/memberships` and `POST /auth/register` answer 400 `invalid_invite`).
- `POST /auth/change-password` with a wrong current password answers **422** `validation_error`
  with `fields.current_password` (so it never triggers the 401-refresh logic).
- Promoters verify their @username through the same OAuth flow, but **no row is stored in
  `instagram_accounts`** for them (no token is kept): `GET /instagram/account` returns
  `{ "account": null }` for promoters; verification shows in `promoter_profile.verified`.
  Callback error reasons: `denied`, `invalid_state`, `exchange_failed`, `instagram_error`,
  `username_mismatch`, `already_connected`. `DELETE /instagram/account` as a promoter clears the verification.
- `GET /dev/instagram/authorize` also accepts `hint` (mock @username to connect). `redirect_uri`
  must equal `${APP_URL}/api/v1/instagram/callback`. `POST /dev/simulate/comment` answers 400
  `validation_error` when the pipeline drops the event (e.g. campaign with `points_comment = 0`).
- `GET /meta/data-deletion/{code}` was added (status page referenced by the `url` returned by
  `POST /meta/data-deletion`).
- `total_earned` and leaderboards count `earn` transactions only (manual adjustments do not rank).
- The interaction time window tolerates 30 s before `starts_at` (events carry second precision).
- `POST /redemptions/{id}/fulfill|cancel` accept an empty body.
- `GET /promoter/home|leaderboard|rewards` without `org_id` use the oldest approved membership;
  campaigns, redemptions and transactions without `org_id` span all approved memberships.
- Extra env vars: `TRUSTED_PROXY_HOPS` (default 1), `RATE_LIMIT_MULTIPLIER` (0 = auto: x100 in
  development), `RL_*` limits, `UPLOAD_DIR`, `POSTGRES_USER/PASSWORD/DB` (compose).

### Review-fix additions (v2)

- **Publishing is idempotent**: the container id is stored on the campaign before `media_publish`;
  re-dispatching reconciles by container status (already published: recovers the media id, never
  publishes twice; never creates a second container while one is pending). The worker also
  retries `subscribed_apps` for accounts with `webhook_subscribed = false`.
- **One open campaign per post**: partial unique index on `(organization_id, ig_media_id)` where
  the status is not `ended`; creating a second one answers **409 `conflict`** ("Já existe uma
  campanha em andamento para este post."). Concurrent dispatches activate and notify exactly once.
- **Dispatch validates the window** with the effective start: `ends_at` already past or not after
  the start answers **400 `validation_error`** with `fields.ends_at`.
- `/promoter/redemptions` and `/promoter/transactions` without `org_id` only span **approved**
  memberships (a removed/pending member sees none).
- New notification type `username_changed` (manager). `PATCH /promoter/profile` may leave the
  promoter's memberships `pending`; clients should refetch `GET /promoter/memberships`.
- New env vars: `TRUSTED_PROXY_CIDRS`, `SYNC_PAGE_SIZE`, `SYNC_PAGES_PER_RUN`. New columns:
  `memberships.approved_by`, `campaigns.publish_container_id`, `publish_container_at`,
  `sync_cursor`, `sync_full_pass_at` (migration 0002).
- Unhandled-error (500) responses carry the same security headers and `X-Request-ID` as every other response.
