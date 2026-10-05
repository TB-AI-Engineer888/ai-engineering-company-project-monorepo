"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AccountPanel, fieldClassName, TextLink } from "@/components/account-panel";
import { accountFetch, readAccountError, setSessionToken } from "@/lib/account";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const reset = searchParams.get("reset");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    const response = await accountFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setPending(false);
    if (!response.ok) {
      setError(await readAccountError(response));
      return;
    }
    const payload = (await response.json()) as { token: string };
    setSessionToken(payload.token);
    router.push("/account");
  }

  return (
    <AccountPanel title="Sign in" description="Use the email and password for your HealthCore account.">
      {reset ? (
        <p role="status" className="text-sm text-foreground">
          Your password was updated. Sign in with the new one.
        </p>
      ) : null}
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <label className="flex flex-col gap-2 text-sm font-medium">
          Email
          <input
            className={fieldClassName}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-2 text-sm font-medium">
          Password
          <input
            className={fieldClassName}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <Button type="submit" className="h-10 w-full" disabled={pending}>
          {pending ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <TextLink href="/forgot-password">Forgot your password?</TextLink>
      <TextLink href="/register">Create an account</TextLink>
    </AccountPanel>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
