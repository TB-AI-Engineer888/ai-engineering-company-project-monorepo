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

  const response = await fetch(path, { ...init, headers });

  if (options.session && response.status === 401 && options.redirectOn401 !== false) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let fields: FieldErrors = {};
    try {
      const payload = (await response.json()) as {
        error?: unknown;
        detail?: unknown;
        fields?: unknown;
      };
      if (typeof payload.error === "string") message = payload.error;
      else if (typeof payload.detail === "string") message = payload.detail;
      if (payload.fields && typeof payload.fields === "object") {
        fields = Object.fromEntries(
          Object.entries(payload.fields as Record<string, unknown>).filter(
            (entry): entry is [string, string] => typeof entry[1] === "string",
          ),
        );
      }
    } catch {
      message = `Request failed (${response.status})`;
    }
    throw new ApiError(message, response.status, fields);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
