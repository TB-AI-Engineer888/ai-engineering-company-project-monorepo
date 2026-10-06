import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl space-y-4 rounded-xl border border-border bg-card px-5 py-8">
      <h2 className="text-xl font-semibold tracking-tight">That page does not exist</h2>
      <p className="text-sm text-muted-foreground">
        The address is not part of the Patient Experience backoffice. Return to the operations
        overview, or contact HealthCore support if you followed a link from inside the clinic network.
      </p>
      <Link href="/" className="inline-flex text-sm underline underline-offset-4">
        Back to operations overview
      </Link>
    </div>
  );
}
