"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AccountPanel, fieldClassName, TextLink } from "@/components/account-panel";
import { accountFetch, readAccountError, setSessionToken } from "@/lib/account";
import { passwordConfirmationError } from "@/lib/password-rules";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const problem = passwordConfirmationError(password, confirmation);
    if (problem) {
      setError(problem);
      return;
    }
    setPending(true);
    setError("");
    const response = await accountFetch("/auth/register", {
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
    <AccountPanel title="Create an account" description="Register the email you will use to sign in.">
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
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-2 text-sm font-medium">
          Confirm password
          <input
            className={fieldClassName}
            type="password"
            autoComplete="new-password"
            required
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </label>
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <Button type="submit" className="h-10 w-full" disabled={pending}>
          {pending ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <TextLink href="/login">Sign in</TextLink>
    </AccountPanel>
  );
}
