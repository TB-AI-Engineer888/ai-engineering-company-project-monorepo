"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ClinicSelect, QuantityField, SupplySelect } from "@/components/inventory/supply-fields";
import { useMedicalSupplies } from "@/components/inventory/use-medical-supplies";
import { ApiError } from "@/lib/http";
import { createSupplyDelivery } from "@/lib/inventory";
import { briefingCategory, clinicCountry, daysUntilExpiry, recordInventoryRejection } from "@/services/inventory-events";
import { track } from "@/services/telemetry";

type Step = "none" | "supply" | "quantity" | "vendor" | "clinic";

export function InboundOrderForm() {
  const searchParams = useSearchParams();
  const { supplies, error: loadError, loading } = useMedicalSupplies();
  const [supplyId, setSupplyId] = useState(searchParams.get("supply") ?? "");
  const [quantity, setQuantity] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [clinicId, setClinicId] = useState("");
  const [lotId, setLotId] = useState("");
  const [expiresOn, setExpiresOn] = useState("");
  const [totalCost, setTotalCost] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const submitted = useRef(false);
  const step = useRef<Step>("none");

  useEffect(() => {
    if (clinicId) step.current = "clinic";
    else if (vendorName.trim()) step.current = "vendor";
    else if (quantity) step.current = "quantity";
    else if (supplyId) step.current = "supply";
    else step.current = "none";
  }, [clinicId, vendorName, quantity, supplyId]);

  useEffect(() => {
    const started = Date.now();
    return () => {
      if (submitted.current) return;
      const seconds = Math.floor((Date.now() - started) / 1000);
      if (seconds < 2) return;
      track("backoffice_flow_abandoned", {
        flow: "inbound_order",
        last_completed_step: step.current,
        time_on_form_seconds: Math.min(seconds, 86400),
      });
    };
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setConfirmation(null);
    setPending(true);
    const supply = supplies.find((item) => item.id === Number(supplyId));
    const cost = Number(totalCost);
    if (!Number.isFinite(cost) || cost < 0) {
      setFormError("Enter the receipt cost in the clinic currency.");
      setPending(false);
      return;
    }
    try {
      const saved = await createSupplyDelivery({
        supply_id: Number(supplyId),
        quantity: Number(quantity),
        vendor_name: vendorName.trim(),
        clinic_id: Number(clinicId),
      });
      submitted.current = true;
      const country = clinicCountry(saved.clinic_id);
      const productCategory = supply ? briefingCategory(supply.category) : null;
      if (supply && country && productCategory) {
        track("inbound_order_created", {
          clinic_id: saved.clinic_id,
          country,
          product_id: saved.supply_id,
          product_category: productCategory,
          quantity: saved.quantity,
          order_id: saved.id,
          vendor_name: saved.vendor_name,
          sku: supply.sku,
          unit: supply.unit,
          country_mismatch: supply.country !== country,
          total_cost: cost,
        });
        const days = daysUntilExpiry(expiresOn);
        if (lotId.trim() && days !== null && days <= 30) {
          track("supply_expiry_flagged", {
            clinic_id: saved.clinic_id,
            country,
            product_id: saved.supply_id,
            product_category: productCategory,
            quantity: saved.quantity,
            lot_id: lotId.trim(),
            expires_on: expiresOn,
            days_to_expiry: days,
            trigger: "receipt",
          });
        }
      }
      setSupplyId("");
      setQuantity("");
      setVendorName("");
      setClinicId("");
      setLotId("");
      setExpiresOn("");
      setTotalCost("");
      setConfirmation(`${saved.quantity} units are now on the supply record.`);
    } catch (caught) {
      if (caught instanceof ApiError) recordInventoryRejection("/inventory/orders/inbound", caught);
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
      <div className="space-y-2">
        <Label htmlFor="total_cost">Total cost</Label>
        <Input
          id="total_cost"
          name="total_cost"
          type="number"
          min="0"
          step="0.01"
          inputMode="decimal"
          value={totalCost}
          onChange={(event) => setTotalCost(event.target.value)}
          required
        />
        <p className="text-sm text-muted-foreground">Clinic currency. USD for US clinics, GBP for UK clinics.</p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="lot_id">Lot</Label>
        <Input
          id="lot_id"
          name="lot_id"
          value={lotId}
          onChange={(event) => setLotId(event.target.value)}
          autoComplete="off"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="expires_on">Expires on</Label>
        <Input
          id="expires_on"
          name="expires_on"
          type="date"
          value={expiresOn}
          onChange={(event) => setExpiresOn(event.target.value)}
        />
        <p className="text-sm text-muted-foreground">Optional. Used when this lot expires within 30 days.</p>
      </div>
      <Button type="submit" disabled={pending || supplies.length === 0}>
        {pending ? "Recording delivery…" : "Record delivery"}
      </Button>
    </form>
  );
}
