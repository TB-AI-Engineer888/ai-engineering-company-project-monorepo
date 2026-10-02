"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AccountPanel, fieldClassName, TextLink } from "@/components/account-panel";
import { accountFetch, readAccountError } from "@/lib/account";
import { passwordConfirmationError } from "@/lib/password-rules";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState(
    token ? "" : "This reset link is invalid or has expired.",
  );
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
    const response = await accountFetch("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: password }),
    });
    setPending(false);
    if (!response.ok) {
      setError(await readAccountError(response));
      return;
    }
    router.push("/login?reset=1");
  }

  return (
    <AccountPanel title="Choose a new password" description="This link works once and expires after 30 minutes.">
      {token ? (
        <form className="flex flex-col gap-4" onSubmit={onSubmit}>
          <label className="flex flex-col gap-2 text-sm font-medium">
            New password
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
            Confirm new password
            <input
              className={fieldClassName}
              type="password"
              autoComplete="new-password"
              required
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
          </label>
          <Button type="submit" className="h-10 w-full" disabled={pending}>
            {pending ? "Updating…" : "Update password"}
          </Button>
        </form>
      ) : null}
      {error ? (
        <div className="flex flex-col gap-2">
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
          <TextLink href="/forgot-password">Request a new reset link</TextLink>
        </div>
      ) : null}
    </AccountPanel>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
