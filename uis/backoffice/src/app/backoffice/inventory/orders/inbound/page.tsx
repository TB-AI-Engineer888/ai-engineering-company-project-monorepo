import { Suspense } from "react";
import { InboundOrderForm } from "@/components/inventory/inbound-order-form";

export default function InboundOrderPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Log a delivery</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Record a vendor shipment received at a HealthCore clinic.
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading the delivery form…</p>}>
        <InboundOrderForm />
      </Suspense>
    </div>
  );
}
