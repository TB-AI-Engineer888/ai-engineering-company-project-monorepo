import { ProductsTable, StockLegend } from "@/components/inventory/products-table";

export default function MedicalSuppliesPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight">Medical supplies</h2>
        <p className="text-sm text-muted-foreground">
          Current stock is deliveries minus consumptions. It is not edited on this page.
        </p>
        <StockLegend />
      </div>
      <ProductsTable />
    </div>
  );
}
