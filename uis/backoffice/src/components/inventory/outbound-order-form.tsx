"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { CONSUMPTION_TYPE_LABELS } from "@/components/inventory/labels";
import { ClinicSelect, QuantityField, selectClass, SupplySelect } from "@/components/inventory/supply-fields";
import { useMedicalSupplies } from "@/components/inventory/use-medical-supplies";
import { ApiError } from "@/lib/http";
import { createSupplyConsumption, readMedicalSupply } from "@/lib/inventory";
import { quantityExceedsStock } from "@/lib/stock-level";

export function OutboundOrderForm() {
  const searchParams = useSearchParams();
  const { supplies, error: loadError, loading } = useMedicalSupplies();
  const [supplyId, setSupplyId] = useState(searchParams.get("supply") ?? "");
  const [quantity, setQuantity] = useState("");
  const [consumptionType, setConsumptionType] = useState("");
  const [clinicId, setClinicId] = useState("");
  const [stock, setStock] = useState<{ id: string; available: number } | null>(null);
  const [stockError, setStockError] = useState<{ id: string; message: string } | null>(null);
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!supplyId) return;
    let cancelled = false;
    readMedicalSupply(Number(supplyId))
      .then((supply) => {
        if (!cancelled) setStock({ id: supplyId, available: supply.current_stock });
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setStockError({
            id: supplyId,
            message: caught instanceof Error ? caught.message : "Could not load current stock.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [supplyId]);

  const available = stock?.id === supplyId ? stock.available : null;
  const visibleStockError = stockError?.id === supplyId ? stockError.message : null;
  const parsedQuantity = Number(quantity);
  const warning =
    available !== null && quantity !== "" && quantityExceedsStock(parsedQuantity, available)
      ? `This quantity is higher than the available stock (${available}).`
      : null;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setQuantityError(null);
    setConfirmation(null);
    setPending(true);
    try {
      const saved = await createSupplyConsumption({
        supply_id: Number(supplyId),
        quantity: parsedQuantity,
        consumption_type: consumptionType as "clinical_use" | "expiry_waste",
        clinic_id: Number(clinicId),
      });
      setQuantity("");
      setConsumptionType("");
      setClinicId("");
      const refreshed = await readMedicalSupply(saved.supply_id);
      setStock({ id: String(saved.supply_id), available: refreshed.current_stock });
      setConfirmation(`${refreshed.current_stock} units remain.`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400) {
        setQuantityError(caught.message);
      } else {
        setFormError(caught instanceof Error ? caught.message : "Could not record this consumption.");
      }
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
          <AlertTitle>Consumption recorded</AlertTitle>
          <AlertDescription>{confirmation}</AlertDescription>
        </Alert>
      ) : null}
      {formError ? (
        <Alert variant="destructive">
          <AlertTitle>Consumption was not recorded</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      ) : null}
      <SupplySelect
        supplies={supplies}
        value={supplyId}
        onChange={(next) => {
          setSupplyId(next);
          setQuantityError(null);
        }}
      />
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {supplyId
          ? available === null
            ? (visibleStockError ?? "Loading current stock…")
            : `Available stock: ${available}`
          : "Select a medical supply to see the available stock."}
      </p>
      <QuantityField
        value={quantity}
        onChange={(next) => {
          setQuantity(next);
          setQuantityError(null);
        }}
        warning={warning}
        error={quantityError}
      />
      <div className="space-y-2">
        <Label htmlFor="consumption_type">Consumption type</Label>
        <select
          id="consumption_type"
          name="consumption_type"
          className={selectClass}
          value={consumptionType}
          onChange={(event) => setConsumptionType(event.target.value)}
          required
        >
          <option value="">Select a consumption type</option>
          {Object.entries(CONSUMPTION_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <ClinicSelect value={clinicId} onChange={setClinicId} />
      <Button type="submit" disabled={pending || supplies.length === 0}>
        {pending ? "Recording consumption…" : "Record consumption"}
      </Button>
    </form>
  );
}
