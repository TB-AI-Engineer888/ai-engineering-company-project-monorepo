"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { CONSUMPTION_TYPE_LABELS, DEPARTMENT_LABELS } from "@/components/inventory/labels";
import { ClinicSelect, QuantityField, selectClass, SupplySelect } from "@/components/inventory/supply-fields";
import { useMedicalSupplies } from "@/components/inventory/use-medical-supplies";
import { ApiError } from "@/lib/http";
import { createSupplyConsumption, listInventoryOrders, readMedicalSupply } from "@/lib/inventory";
import { quantityExceedsStock } from "@/lib/stock-level";
import {
  briefingCategory,
  claimThreshold,
  clinicCountry,
  clinicStock,
  recordInventoryRejection,
  STOCK_THRESHOLD,
  thresholdBand,
} from "@/services/inventory-events";
import { track } from "@/services/telemetry";

export function OutboundOrderForm() {
  const searchParams = useSearchParams();
  const { supplies, error: loadError, loading } = useMedicalSupplies();
  const [supplyId, setSupplyId] = useState(searchParams.get("supply") ?? "");
  const [quantity, setQuantity] = useState("");
  const [consumptionType, setConsumptionType] = useState("");
  const [department, setDepartment] = useState("");
  const [clinicId, setClinicId] = useState("");
  const [stock, setStock] = useState<{ id: string; available: number } | null>(null);
  const [stockError, setStockError] = useState<{ id: string; message: string } | null>(null);
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const submitted = useRef(false);
  const step = useRef<"none" | "supply" | "quantity" | "consumption_type" | "clinic">("none");

  useEffect(() => {
    if (clinicId) step.current = "clinic";
    else if (consumptionType) step.current = "consumption_type";
    else if (quantity) step.current = "quantity";
    else if (supplyId) step.current = "supply";
    else step.current = "none";
  }, [clinicId, consumptionType, quantity, supplyId]);

  useEffect(() => {
    const started = Date.now();
    return () => {
      if (submitted.current) return;
      const seconds = Math.floor((Date.now() - started) / 1000);
      if (seconds < 2) return;
      track("backoffice_flow_abandoned", {
        flow: "outbound_order",
        last_completed_step: step.current,
        time_on_form_seconds: Math.min(seconds, 86400),
      });
    };
  }, []);

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
    const supply = supplies.find((item) => item.id === Number(supplyId));
    const country = clinicCountry(Number(clinicId));
    const productCategory = supply ? briefingCategory(supply.category) : null;
    let clinicBefore: number | null = null;
    try {
      const orders = await listInventoryOrders();
      clinicBefore = clinicStock(orders, Number(clinicId), Number(supplyId));
    } catch {
      clinicBefore = null;
    }
    try {
      const saved = await createSupplyConsumption({
        supply_id: Number(supplyId),
        quantity: parsedQuantity,
        consumption_type: consumptionType as "clinical_use" | "expiry_waste",
        clinic_id: Number(clinicId),
        department,
      });
      submitted.current = true;
      let globalAfter = available === null ? 0 : Math.max(0, available - saved.quantity);
      try {
        const refreshed = await readMedicalSupply(saved.supply_id);
        globalAfter = Math.max(0, refreshed.current_stock);
        setStock({ id: String(saved.supply_id), available: refreshed.current_stock });
      } catch {
        globalAfter = available === null ? 0 : Math.max(0, available - saved.quantity);
      }
      if (supply && country && productCategory && clinicBefore !== null) {
        const clinicAfter = Math.max(0, clinicBefore - saved.quantity);
        track("outbound_order_created", {
          clinic_id: saved.clinic_id,
          country,
          product_id: saved.supply_id,
          product_category: productCategory,
          quantity: saved.quantity,
          department,
          order_id: saved.id,
          consumption_type: saved.consumption_type,
          sku: supply.sku,
          clinic_stock_after: clinicAfter,
          global_stock_after: globalAfter,
        });
        const band = thresholdBand(clinicBefore, clinicAfter);
        if (band && claimThreshold(saved.clinic_id, saved.supply_id, band)) {
          track("stock_threshold_triggered", {
            clinic_id: saved.clinic_id,
            country,
            product_id: saved.supply_id,
            product_category: productCategory,
            quantity: clinicAfter,
            threshold_quantity: STOCK_THRESHOLD,
            band,
            stock_before: Math.max(0, clinicBefore),
            trigger_order_id: saved.id,
            trigger_order_kind: "outbound",
          });
        }
      }
      setQuantity("");
      setConsumptionType("");
      setDepartment("");
      setClinicId("");
      setConfirmation(`${globalAfter} units remain.`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400 && /insufficient stock/i.test(caught.message)) {
        const match = caught.message.match(/Available:\s*(\d+)/i);
        const availableGlobal = match ? Number(match[1]) : Math.max(0, available ?? 0);
        if (supply && country && productCategory && department) {
          track("outbound_order_rejected", {
            clinic_id: Number(clinicId),
            country,
            product_id: supply.id,
            product_category: productCategory,
            quantity: parsedQuantity,
            department,
            available_global: availableGlobal,
            rejection_reason: "insufficient_stock",
          });
        }
        setQuantityError(caught.message);
      } else if (caught instanceof ApiError) {
        recordInventoryRejection("/inventory/orders/outbound", caught);
        setFormError(caught.message);
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
      <div className="space-y-2">
        <Label htmlFor="department">Department</Label>
        <select
          id="department"
          name="department"
          className={selectClass}
          value={department}
          onChange={(event) => setDepartment(event.target.value)}
          required
        >
          <option value="">Select a department</option>
          {Object.entries(DEPARTMENT_LABELS).map(([value, label]) => (
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
