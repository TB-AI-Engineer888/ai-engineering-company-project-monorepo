import { clearToken, getToken } from "@/lib/session";

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  status: number;
  fields: FieldErrors;

  constructor(message: string, status: number, fields: FieldErrors = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields;
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

  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(
      "We could not reach HealthCore. Check your connection and try again.",
      0,
    );
  }

  if (options.session && response.status === 401 && options.redirectOn401 !== false) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
  }

  if (!response.ok) {
    let message = fallbackMessage(response.status);
    let fields: FieldErrors = {};
    try {
      const payload = (await response.json()) as {
        error?: unknown;
        detail?: unknown;
        fields?: unknown;
      } | null;
      const raw = payload?.error ?? payload?.detail;
      if (typeof raw === "string") message = publicMessage(raw, response.status);
      if (payload?.fields && typeof payload.fields === "object") {
        fields = Object.fromEntries(
          Object.entries(payload.fields as Record<string, unknown>).filter(
            (entry): entry is [string, string] => typeof entry[1] === "string",
          ),
        );
      }
      if (Array.isArray(payload?.detail)) {
        for (const item of payload.detail) {
          if (!item || typeof item !== "object") continue;
          const row = item as { loc?: unknown; msg?: unknown };
          const text = publicMessage(
            typeof row.msg === "string" ? row.msg : "Check this field.",
            response.status,
          );
          const loc = Array.isArray(row.loc) ? row.loc.filter((part): part is string => typeof part === "string") : [];
          const field = loc.at(-1);
          if (field && field !== "body") fields[field] = text;
          message = text;
        }
      }
      if (typeof raw === "string" && /email already registered/i.test(raw)) {
        fields.email = "An account with this email already exists.";
        message = fields.email;
      }
    } catch {
      message = fallbackMessage(response.status);
    }
    throw new ApiError(message, response.status, fields);
  }

  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      "The server response could not be read. Try again, or contact HealthCore support.",
      response.status,
    );
  }
}

function looksTechnical(message: string): boolean {
  return /unexpected token|json|syntaxerror|traceback|stack|status code|field required|request failed|\b[1-5]\d\d\b|pat-\d|secret_key|postgresql:\/\/|\/home\/|\/workspace\//i.test(
    message,
  );
}

function publicMessage(message: string, status: number): string {
  const text = message.trim();
  if (/email already registered/i.test(text)) {
    return "An account with this email already exists.";
  }
  if (!text || looksTechnical(text)) {
    return fallbackMessage(status);
  }
  return text;
}

function fallbackMessage(status: number): string {
  if (status === 401) return "Sign in to continue.";
  if (status === 403) return "You do not have access to that action.";
  if (status === 404) return "That item is not available.";
  if (status === 400 || status === 422) return "Check the information and try again.";
  return "Something went wrong. Try again, or contact HealthCore support.";
}
