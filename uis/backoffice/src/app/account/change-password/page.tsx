"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AccountPanel, fieldClassName } from "@/components/account-panel";
import { accountFetch, getSessionToken, readAccountError } from "@/lib/account";
import { passwordConfirmationError } from "@/lib/password-rules";

export default function ChangePasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!getSessionToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const problem = passwordConfirmationError(password, confirmation);
    if (problem) {
      setError(problem);
      setSuccess("");
      return;
    }
    setPending(true);
    setError("");
    setSuccess("");
    const response = await accountFetch("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: password,
      }),
    });
    setPending(false);
    if (response.status === 401) {
      router.replace("/login");
      return;
    }
    if (!response.ok) {
      setError(await readAccountError(response));
      return;
    }
    setCurrentPassword("");
    setPassword("");
    setConfirmation("");
    setSuccess("Your password has been changed.");
  }

  if (!ready) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }

  return (
    <AccountPanel
      title="Change password"
      description="Enter your current password, then choose a new one."
    >
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <label className="flex flex-col gap-2 text-sm font-medium">
          Current password
          <input
            className={fieldClassName}
            type="password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
        </label>
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
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        {success ? (
          <p role="status" className="text-sm text-foreground">
            {success}
          </p>
        ) : null}
        <Button type="submit" className="h-10 w-full" disabled={pending}>
          {pending ? "Updating…" : "Change password"}
        </Button>
      </form>
    </AccountPanel>
  );
}
