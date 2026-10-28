"use client";

import { CLINIC_IDS } from "@/components/inventory/labels";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { MedicalSupply } from "@/lib/inventory";
import { cn } from "@/lib/utils";

export const selectClass =
  "h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export function SupplySelect({
  supplies,
  value,
  onChange,
}: {
  supplies: MedicalSupply[];
  value: string;
  onChange: (supplyId: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor="supply_id">Medical supply</Label>
      <select
        id="supply_id"
        name="supply_id"
        className={selectClass}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
      >
        <option value="">Select a medical supply</option>
        {supplies.map((supply) => (
          <option key={supply.id} value={supply.id}>
            {supply.name}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ClinicSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (clinicId: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor="clinic_id">Clinic</Label>
      <select
        id="clinic_id"
        name="clinic_id"
        className={selectClass}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
      >
        <option value="">Select a clinic</option>
        {CLINIC_IDS.map((clinicId) => (
          <option key={clinicId} value={clinicId}>
            Clinic {clinicId}
          </option>
        ))}
      </select>
    </div>
  );
}

export function QuantityField({
  value,
  onChange,
  warning,
  error,
}: {
  value: string;
  onChange: (quantity: string) => void;
  warning?: string | null;
  error?: string | null;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor="quantity">Quantity</Label>
      <Input
        id="quantity"
        name="quantity"
        type="number"
        min={1}
        step={1}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        required
      />
      {warning ? <p className="text-sm text-amber-800">{warning}</p> : null}
      {error ? (
        <p className={cn("text-sm text-destructive")} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
