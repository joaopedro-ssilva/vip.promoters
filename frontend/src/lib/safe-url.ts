/**
 * URL helpers. Anything coming from the API or from the query string is
 * validated here before it reaches an href / src / navigation.
 */

/** https:// URL (or same-origin relative path) usable as href/src; otherwise null. */
export function safeUrl(value: string | null | undefined): string | null {
  if (!value || typeof value !== "string") return null;
  const v = value.trim();
  if (isSafeRelativePath(v)) return v;
  try {
    const u = new URL(v);
    // our own origin (uploaded files served by the backend under APP_URL; http in local dev)
    if (typeof window !== "undefined" && u.origin === window.location.origin) {
      const rel = `${u.pathname}${u.search}`;
      return isSafeRelativePath(rel) ? rel : null;
    }
    return u.protocol === "https:" ? u.toString() : null;
  } catch {
    return null;
  }
}

/** Same-origin relative path: one leading "/", no "//", no backslash, no control chars/whitespace. */
export function isSafeRelativePath(value: string): boolean {
  if (!value.startsWith("/") || value.startsWith("//")) return false;
  if (/[\u0000- \u007f\\]/.test(value)) return false;
  return true;
}

/** Validates a `next` query parameter; falls back when unsafe. */
export function safeNext(value: string | null | undefined, fallback: string): string {
  if (!value) return fallback;
  return isSafeRelativePath(value) ? value : fallback;
}

/**
 * URL we are willing to navigate the whole browser to (OAuth authorize URL).
 * https anywhere, relative same-origin paths, or http on localhost (dev/mock).
 */
export function safeNavigationUrl(value: string | null | undefined): string | null {
  const ok = safeUrl(value);
  if (ok) return ok;
  if (!value) return null;
  try {
    const u = new URL(value.trim());
    if (
      u.protocol === "http:" &&
      (u.hostname === "localhost" || u.hostname === "127.0.0.1")
    ) {
      return u.toString();
    }
  } catch {
    /* ignore */
  }
  return null;
}
