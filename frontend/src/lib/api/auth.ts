import { api } from "./client";
import type { AppConfig, Role, User } from "./types";

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
  role: Role;
  organization_name?: string;
  instagram_username?: string;
  claim_username?: boolean;
  invite_code?: string;
}

export const authApi = {
  config: () => api.get<AppConfig>("/config"),
  me: () => api.get<{ user: User }>("/auth/me").then((r) => r.user),
  login: (body: { email: string; password: string }) =>
    api.post<{ user: User }>("/auth/login", body).then((r) => r.user),
  register: (body: RegisterInput) =>
    api.post<{ user: User }>("/auth/register", body).then((r) => r.user),
  logout: () => api.post<void>("/auth/logout"),
  updateMe: (body: { name: string }) =>
    api.patch<{ user: User }>("/auth/me", body).then((r) => r.user),
  changePassword: (body: { current_password: string; new_password: string }) =>
    api.post<void>("/auth/change-password", body),
  deleteAccount: (body: { password: string; confirmation: string }) =>
    api.post<void>("/auth/delete-account", body),
};
