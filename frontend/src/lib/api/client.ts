/**
 * Typed fetch wrapper for the backend (same-origin /api/v1).
 * - sends the CSRF header on every request
 * - parses the {error:{code,message,fields}} envelope into ApiError
 * - on a 401 from a non-/auth/ endpoint, refreshes the session once
 *   (de-duplicated across concurrent requests) and retries
 */

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields?: Record<string, string>;
  readonly retryAfter?: number;

  constructor(
    status: number,
    code: string,
    message: string,
    fields?: Record<string, string>,
    retryAfter?: number,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.retryAfter = retryAfter;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

export function errorMessage(e: unknown, fallback = "Algo deu errado. Tente novamente."): string {
  if (e instanceof ApiError) return e.message || fallback;
  return fallback;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  query?: Query;
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
}

let unauthorizedHandler: (() => void) | null = null;
/** Registered by the auth provider: clears client state and goes to /entrar. */
export function setUnauthorizedHandler(fn: (() => void) | null) {
  unauthorizedHandler = fn;
}

function buildUrl(path: string, query?: Query): string {
  const url = `${API_BASE}${path}`;
  if (!query) return url;
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const qs = sp.toString();
  return qs ? `${url}?${qs}` : url;
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "unknown";
  let message = "Não foi possível concluir a operação. Tente novamente.";
  let fields: Record<string, string> | undefined;
  try {
    const data = await res.json();
    const err = data?.error;
    if (err && typeof err === "object") {
      if (typeof err.code === "string") code = err.code;
      if (typeof err.message === "string") message = err.message;
      if (err.fields && typeof err.fields === "object") fields = err.fields;
    }
  } catch {
    // non-JSON error body (for instance a proxy 502)
    if (res.status >= 500) {
      message = "O servidor está indisponível no momento. Tente novamente em instantes.";
    }
  }
  const ra = Number(res.headers.get("Retry-After"));
  return new ApiError(
    res.status,
    code,
    message,
    fields,
    Number.isFinite(ra) && ra > 0 ? ra : undefined,
  );
}

async function rawFetch(method: string, path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {
    "X-Requested-With": "XMLHttpRequest",
    Accept: "application/json",
  };
  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form; // the browser sets the multipart boundary
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  try {
    return await fetch(buildUrl(path, opts.query), {
      method,
      headers,
      body,
      credentials: "same-origin",
      signal: opts.signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(
      0,
      "network_error",
      "Sem conexão com o servidor. Verifique sua internet e tente novamente.",
    );
  }
}

let refreshing: Promise<boolean> | null = null;

/** POST /auth/refresh, shared by every concurrent caller. Resolves true on success. */
export function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await rawFetch("POST", "/auth/refresh", {});
        return res.ok;
      } catch {
        return false;
      } finally {
        // allow a new refresh cycle once this one has settled
        setTimeout(() => {
          refreshing = null;
        }, 0);
      }
    })();
  }
  return refreshing;
}

export async function request<T>(
  method: string,
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  let res = await rawFetch(method, path, opts);

  if (res.status === 401 && !path.startsWith("/auth/")) {
    const ok = await refreshSession();
    if (ok) res = await rawFetch(method, path, opts);
    if (!ok || res.status === 401) {
      unauthorizedHandler?.();
      throw new ApiError(
        401,
        "unauthenticated",
        "Sua sessão expirou. Entre novamente para continuar.",
      );
    }
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(res.status, "invalid_response", "Resposta inesperada do servidor.");
  }
}

export const api = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) =>
    request<T>("GET", path, { query, signal }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, { form }),
};
