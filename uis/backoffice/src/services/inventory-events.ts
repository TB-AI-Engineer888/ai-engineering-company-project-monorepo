import type { ApiError } from "@/lib/http";
import { track } from "@/services/telemetry";

export const STOCK_THRESHOLD = 10;

const STORED_CATEGORY: Record<string, "medication" | "ppe" | "consumable"> = {
  medications: "medication",
  ppe: "ppe",
  consumables: "consumable",
  wound_care: "consumable",
  diagnostics: "consumable",
};

const VALIDATION_FIELDS = new Set([
  "sku",
  "quantity",
  "clinic_id",
  "supply_id",
  "category",
  "country",
  "consumption_type",
  "vendor_name",
  "department",
  "unit",
  "name",
]);

const FIELD_REASON: Record<string, string> = {
  quantity: "invalid_quantity",
  clinic_id: "invalid_clinic",
  supply_id: "unknown_product",
  category: "invalid_category",
  country: "invalid_country",
  consumption_type: "invalid_consumption_type",
  department: "invalid_department",
};

export function briefingCategory(stored: string): "medication" | "ppe" | "consumable" | null {
  return STORED_CATEGORY[stored] ?? null;
}

export function clinicCountry(clinicId: number): "US" | "UK" | null {
  if (clinicId >= 1 && clinicId <= 9) return "US";
  if (clinicId >= 10 && clinicId <= 12) return "UK";
  return null;
}

export function clinicStock(
  orders: { order_kind: string; clinic_id: number; supply_id: number; quantity: number }[],
  clinicId: number,
  supplyId: number,
): number {
  let total = 0;
  for (const order of orders) {
    if (order.clinic_id !== clinicId || order.supply_id !== supplyId) continue;
    total += order.order_kind === "inbound" ? order.quantity : -order.quantity;
  }
  return total;
}

export function thresholdBand(before: number, after: number): "low" | "out" | null {
  if (after > STOCK_THRESHOLD) return null;
  if (before > STOCK_THRESHOLD && after <= 0) return "out";
  if (before > STOCK_THRESHOLD) return "low";
  if (before > 0 && after <= 0) return "out";
  return null;
}

export function claimThreshold(clinicId: number, productId: number, band: "low" | "out"): boolean {
  if (typeof window === "undefined") return false;
  const day = new Date().toISOString().slice(0, 10);
  const key = `healthcore.telemetry.threshold.${clinicId}.${productId}.${band}.${day}`;
  if (window.localStorage.getItem(key)) return false;
  window.localStorage.setItem(key, "1");
  return true;
}

export function daysUntilExpiry(expiresOn: string, today = new Date()): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(expiresOn)) return null;
  const [year, month, day] = expiresOn.split("-").map(Number);
  if (!year || !month || !day) return null;
  const expiry = Date.UTC(year, month - 1, day);
  const start = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Math.round((expiry - start) / 86_400_000);
}

export function recordInventoryRejection(route: string, error: ApiError): void {
  if (error.status < 400 || error.status > 422) return;
  if (/insufficient stock/i.test(error.message)) return;
  const rawField = Object.keys(error.fields)[0] ?? null;
  let reason = "invalid_body";
  let field = rawField;
  if (error.status === 404 || /not found/i.test(error.message)) {
    reason = "unknown_product";
    field = "supply_id";
  } else if (/already registered/i.test(error.message)) {
    reason = "duplicate_sku";
    field = "sku";
  } else if (rawField && FIELD_REASON[rawField]) {
    reason = FIELD_REASON[rawField];
  }
  track("inventory_validation_failed", {
    route_template: route,
    method: "POST",
    http_status: error.status,
    reason_code: reason,
    field_name: field && VALIDATION_FIELDS.has(field) ? field : null,
  });
}
