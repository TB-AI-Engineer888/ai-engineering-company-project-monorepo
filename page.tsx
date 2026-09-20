import Link from "next/link";
import { FileBarChart } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Operations overview</h2>
        <p className="mt-2 text-muted-foreground">
          Patient coordinators log appointment, billing, clinical care,
          accessibility, and administrative incidents across the clinic
          network. Incident extracts stay on HealthCore systems.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Incident file analyzer</CardTitle>
          <CardDescription>
            Upload a CSV extract to validate records and summarise volume,
            category, status, country, and closed-case satisfaction.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Link
            href="/incidents"
            className={cn(buttonVariants({ size: "lg" }), "w-fit")}
          >
            <FileBarChart data-icon="inline-start" />
            Open incident analyzer
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
