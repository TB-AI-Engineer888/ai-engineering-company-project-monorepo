"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AccountPanel, TextLink } from "@/components/account-panel";
import { accountFetch, clearSessionToken, getSessionToken } from "@/lib/account";

export default function AccountPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getSessionToken()) {
      router.replace("/login");
      return;
    }
    accountFetch("/auth/me")
      .then(async (response) => {
        if (!response.ok) {
          clearSessionToken();
          router.replace("/login");
          return;
        }
        const payload = (await response.json()) as { email: string };
        setEmail(payload.email);
      })
      .catch(() => setError("Your account could not be loaded."));
  }, [router]);

  async function signOut() {
    await accountFetch("/auth/logout", { method: "POST" });
    clearSessionToken();
    router.replace("/login");
  }

  return (
    <AccountPanel title="Your account" description="Signed-in HealthCore account.">
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : (
        <p className="text-sm">{email || "Loading your account…"}</p>
      )}
      <TextLink href="/account/change-password">Change password</TextLink>
      <Button type="button" variant="outline" className="h-10 w-full" onClick={signOut}>
        Sign out
      </Button>
    </AccountPanel>
  );
}
