import { ApiError, apiRequest } from "@/lib/http";
import { clearSession, clearStaffId, clearToken, setStaffId, setToken, startSession } from "@/lib/session";

export type Profile = {
  name: string;
  phone: string;
  address: string;
};

export type Account = {
  email: string;
  profile: Profile;
};

export type SignedIn = {
  role: "admin" | "manager" | "user";
};

export type RegisteredAccount = Account & {
  uuid: string | null;
};

export type RegisterInput = {
  email: string;
  password: string;
  name: string;
  phone: string;
  address: string;
};

export async function registerAccount(input: RegisterInput): Promise<RegisteredAccount> {
  const account = await apiRequest<{ email?: string; uuid?: string | null; profile?: Partial<Profile> | null }>(
    "/users",
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
  if (typeof account.uuid === "string") setStaffId(account.uuid);
  return {
    email: account.email ?? "",
    uuid: typeof account.uuid === "string" ? account.uuid : null,
    profile: profileFrom(account.profile),
  };
}

export async function login(email: string, password: string): Promise<SignedIn> {
  const result = await apiRequest<{ access_token?: string; uuid?: string | null; role?: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!result.access_token) {
    throw new ApiError("The server did not return a session token.", 500);
  }
  setToken(result.access_token);
  if (typeof result.uuid === "string") setStaffId(result.uuid);
  startSession();
  if (result.role === "admin" || result.role === "manager" || result.role === "user") {
    return { role: result.role };
  }
  return { role: "user" };
}

function profileFrom(value: Partial<Profile> | null | undefined): Profile {
  return {
    name: value?.name ?? "",
    phone: value?.phone ?? "",
    address: value?.address ?? "",
  };
}

export async function fetchMe(): Promise<Account> {
  const account = await apiRequest<{ email?: string; uuid?: string | null; profile?: Partial<Profile> | null }>(
    "/auth/me",
    { method: "GET" },
    { session: true, redirectOn401: false },
  );
  if (typeof account.uuid === "string") setStaffId(account.uuid);
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
  clearStaffId();
  clearSession();
  window.location.assign("/login");
}
