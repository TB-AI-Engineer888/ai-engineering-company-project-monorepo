import { HeartPulse } from "lucide-react";

export function AuthFrame({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-md">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <HeartPulse className="size-4" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight">HealthCore</p>
          <p className="text-xs text-muted-foreground">Patient Experience backoffice</p>
        </div>
      </div>
      <div className="rounded-xl bg-card p-5 text-card-foreground ring-1 ring-foreground/10 sm:p-6">
        <h1 className="mb-5 text-xl font-semibold tracking-tight">{title}</h1>
        {children}
      </div>
    </div>
  );
}
