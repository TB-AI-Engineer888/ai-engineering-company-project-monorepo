"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/form-field";
import { login } from "@/lib/auth";
import { ApiError } from "@/lib/http";
import { track } from "@/services/telemetry";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const session = await login(email, password);
      track("login_succeeded", { role: session.role });
      router.replace("/");
    } catch (caught) {
      if (caught instanceof ApiError && caught.failureReason) {
        track("login_failed", { failure_reason: caught.failureReason });
      }
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not sign in</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <FormField
        id="email"
        label="Email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={setEmail}
        required
      />
      <FormField
        id="password"
        label="Password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={setPassword}
        required
      />
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Signing in…" : "Sign in"}
      </Button>
      <p className="text-sm text-muted-foreground">
        Need an account?{" "}
        <Link href="/register" className="font-medium text-foreground underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
