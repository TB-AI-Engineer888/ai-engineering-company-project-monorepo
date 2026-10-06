"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl space-y-4 rounded-xl border border-border bg-card px-5 py-8">
      <h2 className="text-xl font-semibold tracking-tight">This page ran into a problem</h2>
      <p className="text-sm text-muted-foreground">
        The backoffice could not finish loading this view. Try again, return to the operations
        overview, or contact HealthCore support if it continues.
      </p>
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={() => reset()}>
          Try again
        </Button>
        <Link href="/" className="inline-flex h-8 items-center text-sm underline underline-offset-4">
          Back to operations overview
        </Link>
      </div>
    </div>
  );
}
