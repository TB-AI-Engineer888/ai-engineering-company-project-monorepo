import { OrdersTable } from "@/components/inventory/orders-table";

export default function InventoryOrdersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Supply orders</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Deliveries and consumptions, including the staff member who recorded each one. This list is read-only.
        </p>
      </div>
      <OrdersTable />
    </div>
  );
}
