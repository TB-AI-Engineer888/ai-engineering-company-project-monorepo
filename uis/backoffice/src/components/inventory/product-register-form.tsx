"use client";

import { useState } from "react";
import { SUPPLY_CATEGORY_LABELS, SUPPLY_UNIT_LABELS } from "@/components/inventory/labels";
import { selectClass } from "@/components/inventory/supply-fields";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/http";
import { createMedicalSupply } from "@/lib/inventory";
import { briefingCategory, recordInventoryRejection } from "@/services/inventory-events";
import { track } from "@/services/telemetry";

export function ProductRegisterForm() {
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [country, setCountry] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setConfirmation(null);
    setPending(true);
    try {
      const saved = await createMedicalSupply({
        name: name.trim(),
        sku: sku.trim(),
        category,
        unit,
        country,
      });
      const productCategory = briefingCategory(saved.category);
      if (productCategory && (saved.country === "US" || saved.country === "UK")) {
        track("product_registered", {
          product_id: saved.id,
          sku: saved.sku,
          product_category: productCategory,
          unit: saved.unit,
          country: saved.country,
          quantity: 0,
        });
      }
      setName("");
      setSku("");
      setCategory("");
      setUnit("");
      setCountry("");
      setConfirmation(`${saved.sku} is on the catalogue. Stock starts at zero until a delivery.`);
    } catch (caught) {
      if (caught instanceof ApiError) recordInventoryRejection("/inventory/products", caught);
      setFormError(caught instanceof ApiError ? caught.message : "Could not register this supply.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-xl space-y-4">
      <div>
        <h3 className="text-lg font-semibold tracking-tight">Register a supply</h3>
        <p className="text-sm text-muted-foreground">
          Adds a catalogue row. Stock still changes only through deliveries and consumptions.
        </p>
      </div>
      {confirmation ? (
        <Alert>
          <AlertTitle>Supply registered</AlertTitle>
          <AlertDescription>{confirmation}</AlertDescription>
        </Alert>
      ) : null}
      {formError ? (
        <Alert variant="destructive">
          <AlertTitle>Supply was not registered</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      ) : null}
      <div className="space-y-2">
        <Label htmlFor="product_name">Name</Label>
        <Input id="product_name" value={name} onChange={(event) => setName(event.target.value)} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="sku">SKU</Label>
        <Input id="sku" value={sku} onChange={(event) => setSku(event.target.value)} required autoComplete="off" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="category">Category</Label>
        <select
          id="category"
          className={selectClass}
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          required
        >
          <option value="">Select a category</option>
          {Object.entries(SUPPLY_CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="unit">Unit</Label>
        <select id="unit" className={selectClass} value={unit} onChange={(event) => setUnit(event.target.value)} required>
          <option value="">Select a unit</option>
          {Object.entries(SUPPLY_UNIT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="country">Country</Label>
        <select
          id="country"
          className={selectClass}
          value={country}
          onChange={(event) => setCountry(event.target.value)}
          required
        >
          <option value="">Select a country</option>
          <option value="US">United States</option>
          <option value="UK">United Kingdom</option>
        </select>
      </div>
      <Button type="submit" disabled={pending}>
        {pending ? "Registering…" : "Register supply"}
      </Button>
    </form>
  );
}
