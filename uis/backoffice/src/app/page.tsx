import Link from "next/link";
import { FileBarChart, Package } from "lucide-react";
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
        <p className="mt-2 text-muted-foreground">Medical supply inventory and incident file analysis</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Medical supply inventory</CardTitle>
          <CardDescription>
            Review current stock, record deliveries and consumptions, and read the order history.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link
            href="/backoffice/inventory/products"
            className={cn(buttonVariants({ size: "lg" }), "w-fit")}
          >
            <Package data-icon="inline-start" />
            Open medical supplies
          </Link>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Incident file analyzer</CardTitle>
          <CardDescription>Upload CSV, view summary, export results</CardDescription>
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
