const SESSION_KEY = "healthcore_session";

export function getSessionToken() {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(SESSION_KEY);
}

export function setSessionToken(token: string) {
  sessionStorage.setItem(SESSION_KEY, token);
}

export function clearSessionToken() {
  sessionStorage.removeItem(SESSION_KEY);
}

export async function accountFetch(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);
  const token = getSessionToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(path, { ...init, headers });
}

export async function readAccountError(response: Response) {
  try {
    const payload = (await response.json()) as { error?: string };
    return payload.error || "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}
