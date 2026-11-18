import { clearSession, clearStaffId, clearToken, getToken } from "@/lib/session";
import { recordLatency, track } from "@/services/telemetry";

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  status: number;
  fields: FieldErrors;
  failureReason: string | null;

  constructor(message: string, status: number, fields: FieldErrors = {}, failureReason: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields;
    this.failureReason = failureReason;
  }
}

type RequestOptions = {
  session?: boolean;
  redirectOn401?: boolean;
};

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (options.session) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const startedAt = typeof performance === "undefined" ? 0 : performance.now();
  const response = await fetch(path, { ...init, headers });
  recordLatency(path, init.method ?? "GET", response.status, startedAt);

  if (options.session && response.status === 401) {
    abandonSession(response);
    if (options.redirectOn401 !== false && typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let fields: FieldErrors = {};
    let failureReason: string | null = null;
    try {
      const payload = (await response.json()) as {
        error?: unknown;
        detail?: unknown;
        fields?: unknown;
        failure_reason?: unknown;
      };
      if (
        payload.failure_reason === "unknown_user" ||
        payload.failure_reason === "bad_password" ||
        payload.failure_reason === "inactive_user"
      ) {
        failureReason = payload.failure_reason;
      }
      if (typeof payload.error === "string") message = payload.error;
      else if (typeof payload.detail === "string") message = payload.detail;
      if (payload.fields && typeof payload.fields === "object") {
        fields = Object.fromEntries(
          Object.entries(payload.fields as Record<string, unknown>).filter(
            (entry): entry is [string, string] => typeof entry[1] === "string",
          ),
        );
      }
      if (Array.isArray(payload.detail)) {
        for (const item of payload.detail) {
          if (!item || typeof item !== "object") continue;
          const row = item as { loc?: unknown; msg?: unknown };
          const text = typeof row.msg === "string" ? row.msg : "Check this field.";
          const loc = Array.isArray(row.loc) ? row.loc.filter((part): part is string => typeof part === "string") : [];
          const field = loc.at(-1);
          if (field && field !== "body") fields[field] = text;
          if (message.startsWith("Request failed")) message = text;
        }
      }
      if (typeof payload.error === "string" && /email already registered/i.test(payload.error)) {
        fields.email = "An account with this email already exists.";
        message = fields.email;
      }
    } catch {
      message = `Request failed (${response.status})`;
    }
    throw new ApiError(message, response.status, fields, failureReason);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function abandonSession(response: Response): void {
  const hadToken = Boolean(getToken());
  const reason = response.headers.get("X-Auth-Reason");
  if (hadToken && (reason === "token_expired" || reason === "inactive_user")) {
    track("session_expired", { reason });
  }
  clearToken();
  clearStaffId();
  clearSession();
}
