"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ClinicSelect, QuantityField, SupplySelect } from "@/components/inventory/supply-fields";
import { useMedicalSupplies } from "@/components/inventory/use-medical-supplies";
import { ApiError } from "@/lib/http";
import { createSupplyDelivery } from "@/lib/inventory";

export function InboundOrderForm() {
  const searchParams = useSearchParams();
  const { supplies, error: loadError, loading } = useMedicalSupplies();
  const [supplyId, setSupplyId] = useState(searchParams.get("supply") ?? "");
  const [quantity, setQuantity] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [clinicId, setClinicId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setConfirmation(null);
    setPending(true);
    try {
      const saved = await createSupplyDelivery({
        supply_id: Number(supplyId),
        quantity: Number(quantity),
        vendor_name: vendorName.trim(),
        clinic_id: Number(clinicId),
      });
      setSupplyId("");
      setQuantity("");
      setVendorName("");
      setClinicId("");
      setConfirmation(`${saved.quantity} units are now on the supply record.`);
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "Could not record this delivery.");
    } finally {
      setPending(false);
    }
  }

  if (loading) return <p className="text-sm text-muted-foreground">Loading medical supplies…</p>;
  if (loadError) {
    return (
      <p className="text-sm text-destructive" role="alert">
        {loadError}
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-xl space-y-4">
      {confirmation ? (
        <Alert>
          <AlertTitle>Delivery recorded</AlertTitle>
          <AlertDescription>{confirmation}</AlertDescription>
        </Alert>
      ) : null}
      {formError ? (
        <Alert variant="destructive">
          <AlertTitle>Delivery was not recorded</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      ) : null}
      <SupplySelect supplies={supplies} value={supplyId} onChange={setSupplyId} />
      <QuantityField value={quantity} onChange={setQuantity} />
      <div className="space-y-2">
        <Label htmlFor="vendor_name">Vendor</Label>
        <Input
          id="vendor_name"
          name="vendor_name"
          value={vendorName}
          onChange={(event) => setVendorName(event.target.value)}
          required
        />
      </div>
      <ClinicSelect value={clinicId} onChange={setClinicId} />
      <Button type="submit" disabled={pending || supplies.length === 0}>
        {pending ? "Recording delivery…" : "Record delivery"}
      </Button>
    </form>
  );
}
