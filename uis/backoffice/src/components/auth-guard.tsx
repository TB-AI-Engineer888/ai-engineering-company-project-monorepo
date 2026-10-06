"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { fetchMe } from "@/lib/auth";
import { ApiError } from "@/lib/http";
import { clearToken, getToken } from "@/lib/session";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const validatedToken = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const publicPath = PUBLIC_PATHS.has(pathname);
    const token = getToken();

    async function checkSession() {
      if (!token) {
        validatedToken.current = null;
        if (!cancelled) {
          setSessionError(null);
          setReady(publicPath);
        }
        if (!publicPath) router.replace("/login");
        return;
      }

      if (validatedToken.current !== token) {
        try {
          await fetchMe();
          validatedToken.current = token;
          if (!cancelled) setSessionError(null);
        } catch (caught) {
          const invalid = caught instanceof ApiError && caught.status === 401;
          if (!invalid) {
            if (!cancelled) {
              setSessionError("Could not confirm the session.");
              setReady(false);
            }
            return;
          }
          validatedToken.current = null;
          clearToken();
          if (cancelled) return;
          setSessionError(null);
          setReady(publicPath);
          if (!publicPath) router.replace("/login");
          return;
        }
      }

      if (cancelled) return;
      if (publicPath) {
        router.replace("/");
        return;
      }
      setReady(true);
    }

    if (validatedToken.current !== token) setReady(false);
    void checkSession();
    return () => {
      cancelled = true;
    };
  }, [pathname, router, attempt]);

  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-4 text-center text-sm text-muted-foreground">
        <p>{sessionError ?? "Checking your session…"}</p>
        {sessionError ? (
          <>
            <button type="button" className="underline underline-offset-4" onClick={() => setAttempt((value) => value + 1)}>
              Try again
            </button>
            <Link href="/login" className="underline underline-offset-4">
              Back to sign in
            </Link>
            <p>If this keeps happening, contact HealthCore support.</p>
          </>
        ) : null}
      </div>
    );
  }

  return children;
}
