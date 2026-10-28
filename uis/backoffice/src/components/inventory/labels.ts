export const SUPPLY_CATEGORY_LABELS: Record<string, string> = {
  ppe: "PPE",
  wound_care: "Wound care",
  diagnostics: "Diagnostics",
  medications: "Medications",
  consumables: "Consumables",
};

export const CONSUMPTION_TYPE_LABELS: Record<string, string> = {
  clinical_use: "Clinical use",
  expiry_waste: "Expiry waste",
};

export const CLINIC_IDS = Array.from({ length: 12 }, (_, index) => index + 1);

export function categoryLabel(category: string): string {
  return SUPPLY_CATEGORY_LABELS[category] ?? category;
}

export function consumptionLabel(consumptionType: string): string {
  return CONSUMPTION_TYPE_LABELS[consumptionType] ?? consumptionType;
}

export function orderKindLabel(orderKind: "inbound" | "outbound"): string {
  return orderKind === "inbound" ? "Delivery (inbound)" : "Consumption (outbound)";
}

export function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-CA", { dateStyle: "medium", timeStyle: "short" });
}
