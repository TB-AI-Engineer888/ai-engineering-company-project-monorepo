"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { consumptionLabel, formatWhen, orderKindLabel } from "@/components/inventory/labels";
import { listInventoryOrders, type InventoryOrder } from "@/lib/inventory";

export function OrdersTable() {
  const [orders, setOrders] = useState<InventoryOrder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listInventoryOrders()
      .then((rows) => {
        if (!cancelled) setOrders(rows);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Could not load supply orders.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Loading supply orders…</p>;
  if (error) {
    return (
      <p className="text-sm text-destructive" role="alert">
        {error}
      </p>
    );
  }
  if (orders.length === 0) {
    return <p className="text-sm text-muted-foreground">No deliveries or consumptions have been recorded.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Medical supply</TableHead>
          <TableHead>Quantity</TableHead>
          <TableHead>Order type</TableHead>
          <TableHead>Detail</TableHead>
          <TableHead>Recorded</TableHead>
          <TableHead>User UUID</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {orders.map((order) => (
          <TableRow key={`${order.order_kind}-${order.id}`}>
            <TableCell className="font-medium">{order.supply.name}</TableCell>
            <TableCell>{order.quantity}</TableCell>
            <TableCell>
              <Badge variant={order.order_kind === "inbound" ? "default" : "destructive"}>
                {orderKindLabel(order.order_kind)}
              </Badge>
            </TableCell>
            <TableCell>
              {order.order_kind === "inbound"
                ? order.vendor_name
                : order.consumption_type
                  ? consumptionLabel(order.consumption_type)
                  : ""}
            </TableCell>
            <TableCell>{formatWhen(order.created_at)}</TableCell>
            <TableCell className="font-mono text-xs">{order.user_uuid}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
