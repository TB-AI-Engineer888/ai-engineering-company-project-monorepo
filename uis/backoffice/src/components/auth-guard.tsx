"use client";

import { useEffect, useRef, useState } from "react";
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
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4 text-center text-sm text-muted-foreground">
        {sessionError ?? "Checking your session…"}
      </div>
    );
  }

  return children;
}
