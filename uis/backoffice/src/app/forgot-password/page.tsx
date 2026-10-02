"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { AccountPanel, fieldClassName, TextLink } from "@/components/account-panel";
import { accountFetch } from "@/lib/account";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      await accountFetch("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    } finally {
      setPending(false);
      setSubmitted(true);
    }
  }

  return (
    <AccountPanel
      title="Reset your password"
      description="Enter the email on your account. A reset link will be sent if that address is registered."
    >
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <fieldset disabled={submitted || pending} className="flex flex-col gap-4">
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
          <Button type="submit" className="h-10 w-full" disabled={submitted || pending}>
            {pending ? "Sending…" : "Send reset link"}
          </Button>
        </fieldset>
      </form>
      {submitted ? (
        <p role="status" className="text-sm text-foreground">
          If that address is registered, you&apos;ll receive a link shortly.
        </p>
      ) : null}
      <TextLink href="/login">Back to sign in</TextLink>
    </AccountPanel>
  );
}
