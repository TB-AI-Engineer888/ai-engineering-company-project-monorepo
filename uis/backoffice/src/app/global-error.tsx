"use client";

import Link from "next/link";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "sans-serif", margin: "2rem" }}>
        <h1>HealthCore backoffice is unavailable</h1>
        <p>
          Something went wrong before the page could load. Try again, go back to the home page, or
          contact HealthCore support.
        </p>
        <p>
          <button type="button" onClick={() => reset()}>
            Try again
          </button>
        </p>
        <p>
          <Link href="/">Back to operations overview</Link>
        </p>
      </body>
    </html>
  );
}
