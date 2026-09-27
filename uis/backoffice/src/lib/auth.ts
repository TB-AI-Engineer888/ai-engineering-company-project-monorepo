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
  const result = await apiRequest<{ access_token?: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!result.access_token) {
    throw new ApiError("The server did not return a session token.", 500);
  }
  setToken(result.access_token);
}

function profileFrom(value: Partial<Profile> | null | undefined): Profile {
  return {
    name: value?.name ?? "",
    phone: value?.phone ?? "",
    address: value?.address ?? "",
  };
}

export async function fetchMe(): Promise<Account> {
  const account = await apiRequest<{ email?: string; profile?: Partial<Profile> | null }>(
    "/auth/me",
    { method: "GET" },
    { session: true, redirectOn401: false },
  );
  return {
    email: account.email ?? "",
    profile: profileFrom(account.profile),
  };
}

export async function updateProfile(profile: Profile): Promise<Profile> {
  const saved = await apiRequest<Partial<Profile>>(
    "/profiles/me",
    { method: "PUT", body: JSON.stringify(profile) },
    { session: true },
  );
  return profileFrom(saved);
}

export function logout(): void {
  clearToken();
  window.location.assign("/login");
}
