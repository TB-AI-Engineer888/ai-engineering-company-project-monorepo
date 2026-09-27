import { ApiError, apiRequest } from "@/lib/http";
import { clearToken, setToken } from "@/lib/session";

export type Profile = {
  name: string;
  phone: string;
  address: string;
};

export type Account = {
  email: string;
  profile: Profile;
};

export type RegisterInput = {
  email: string;
  password: string;
  name: string;
  phone: string;
  address: string;
};

export async function registerAccount(input: RegisterInput): Promise<Account> {
  return apiRequest<Account>("/users", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function login(email: string, password: string): Promise<void> {
  const result = await apiRequest<{ token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!result.token) {
    throw new ApiError("The server did not return a session token.", 500);
  }
  setToken(result.token);
}

export async function fetchMe(): Promise<Account> {
  return apiRequest<Account>("/auth/me", { method: "GET" }, { session: true, redirectOn401: false });
}

export async function updateProfile(profile: Profile): Promise<Account> {
  return apiRequest<Account>(
    "/profiles/me",
    { method: "PUT", body: JSON.stringify(profile) },
    { session: true },
  );
}

export function logout(): void {
  clearToken();
  window.location.assign("/login");
}
