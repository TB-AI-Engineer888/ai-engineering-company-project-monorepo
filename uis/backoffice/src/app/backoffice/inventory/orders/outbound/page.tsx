import { Suspense } from "react";
import { OutboundOrderForm } from "@/components/inventory/outbound-order-form";

export default function OutboundOrderPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Log a consumption</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Record clinical use or expiry waste. The available stock is shown before you submit.
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading the consumption form…</p>}>
        <OutboundOrderForm />
      </Suspense>
    </div>
  );
}
