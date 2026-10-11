import { z } from "zod";

/** Invite codes: 8 chars, uppercase letters and digits without 0 O 1 I L; lookups are case-insensitive. */
export const INVITE_ALPHABET = /^[A-HJ-KM-NP-Z2-9]{8}$/;

export const INVITE_MESSAGE = "O código tem 8 caracteres (letras e números, sem 0, O, 1, I ou L).";

export function isValidInviteCode(v: string): boolean {
  return INVITE_ALPHABET.test(v.trim().toUpperCase());
}

/** Optional invite code (empty allowed). */
export const optionalInviteCodeSchema = z
  .string()
  .refine((v) => v.trim() === "" || isValidInviteCode(v), INVITE_MESSAGE);

export const nameSchema = z
  .string()
  .trim()
  .min(2, "Informe pelo menos 2 caracteres.")
  .max(80, "Use no máximo 80 caracteres.");

export const emailSchema = z
  .string()
  .trim()
  .min(1, "Informe seu e-mail.")
  .max(254, "O e-mail é muito longo.")
  .email("Informe um e-mail válido.");

export const passwordSchema = z
  .string()
  .min(8, "A senha precisa ter pelo menos 8 caracteres.")
  .max(128, "A senha pode ter no máximo 128 caracteres.")
  .regex(/[A-Za-z]/, "A senha precisa ter pelo menos uma letra.")
  .regex(/\d/, "A senha precisa ter pelo menos um número.");

export const igUsernameSchema = z
  .string()
  .trim()
  .regex(/^@?[A-Za-z0-9._]{1,30}$/, "Informe um @ do Instagram válido.");

export function normalizeIgUsername(v: string): string {
  return v.trim().replace(/^@/, "").toLowerCase();
}

/** Text → integer, or NaN when not a plain integer. */
export function parseIntStrict(v: string): number {
  const t = v.trim();
  return /^-?\d+$/.test(t) ? Number(t) : Number.NaN;
}
