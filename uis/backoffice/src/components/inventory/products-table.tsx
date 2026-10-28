"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { categoryLabel } from "@/components/inventory/labels";
import { useMedicalSupplies } from "@/components/inventory/use-medical-supplies";
import { stockBand } from "@/lib/stock-level";
import { cn } from "@/lib/utils";

const BAND_CLASS = {
  healthy: "bg-emerald-100 text-emerald-900",
  low: "bg-amber-100 text-amber-950",
  out: "bg-red-100 text-red-900",
} as const;

const BAND_LABEL = {
  healthy: "Healthy stock",
  low: "Low stock",
  out: "Out of stock",
} as const;

export function ProductsTable() {
  const { supplies, error, loading } = useMedicalSupplies();

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading medical supplies…</p>;
  }

  if (error) {
    return (
      <p className="text-sm text-destructive" role="alert">
        {error}
      </p>
    );
  }

  if (supplies.length === 0) {
    return <p className="text-sm text-muted-foreground">No medical supplies are registered yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Medical supply</TableHead>
          <TableHead>SKU</TableHead>
          <TableHead>Category</TableHead>
          <TableHead>Unit</TableHead>
          <TableHead>Country</TableHead>
          <TableHead>Current stock</TableHead>
          <TableHead>Orders</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {supplies.map((supply) => {
          const band = stockBand(supply.current_stock);
          return (
            <TableRow key={supply.id}>
              <TableCell className="font-medium">{supply.name}</TableCell>
              <TableCell>{supply.sku}</TableCell>
              <TableCell>{categoryLabel(supply.category)}</TableCell>
              <TableCell>{supply.unit}</TableCell>
              <TableCell>{supply.country}</TableCell>
              <TableCell>
                <span
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full px-2 py-0.5 text-xs font-medium",
                    BAND_CLASS[band],
                  )}
                >
                  {supply.current_stock}
                  <span>{BAND_LABEL[band]}</span>
                </span>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/backoffice/inventory/orders/inbound?supply=${supply.id}`}
                    className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                  >
                    Log delivery
                  </Link>
                  <Link
                    href={`/backoffice/inventory/orders/outbound?supply=${supply.id}`}
                    className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                  >
                    Log consumption
                  </Link>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export function StockLegend() {
  return (
    <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
      <Badge variant="outline">Healthy: 11 or more</Badge>
      <Badge variant="outline">Low: 1 to 10</Badge>
      <Badge variant="outline">Out: 0</Badge>
    </div>
  );
}
