const TOKEN_KEY = "healthcore.session.token";
const STAFF_KEY = "healthcore.session.staff";
const SESSION_KEY = "healthcore.session.id";

function storage(kind: "localStorage" | "sessionStorage"): Storage {
  return window[kind];
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function getStaffId(): string | null {
  if (typeof window === "undefined") return null;
  return storage("localStorage").getItem(STAFF_KEY);
}

export function setStaffId(staffId: string): void {
  storage("localStorage").setItem(STAFF_KEY, staffId);
}

export function clearStaffId(): void {
  window.localStorage.removeItem(STAFF_KEY);
}

export function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return storage("sessionStorage").getItem(SESSION_KEY);
}

export function startSession(): string {
  const sessionId = crypto.randomUUID();
  storage("sessionStorage").setItem(SESSION_KEY, sessionId);
  return sessionId;
}

export function clearSession(): void {
  window.sessionStorage.removeItem(SESSION_KEY);
}
