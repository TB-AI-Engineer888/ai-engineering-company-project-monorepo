import { ApiError, apiRequest } from "@/lib/http";
import { briefingCategory, clinicCountry } from "@/services/inventory-events";
import { track } from "@/services/telemetry";

export type MedicalSupply = {
  id: number;
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
  current_stock: number;
};

export type SupplySummary = {
  id: number;
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
};

export type InventoryOrder = {
  order_kind: "inbound" | "outbound";
  id: number;
  supply_id: number;
  quantity: number;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
  vendor_name: string | null;
  consumption_type: string | null;
  supply: SupplySummary;
};

export type SupplyDeliveryInput = {
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
};

export type SupplyConsumptionInput = {
  supply_id: number;
  quantity: number;
  consumption_type: "clinical_use" | "expiry_waste";
  clinic_id: number;
  department?: string;
};

export type MedicalSupplyInput = {
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
};

export type SupplyDeliveryRecord = {
  id: number;
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
};

export type SupplyConsumptionRecord = {
  id: number;
  supply_id: number;
  quantity: number;
  consumption_type: string;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
};

function inventoryUrl(path: string): string {
  const configured = process.env.NEXT_PUBLIC_INVENTORY_API_URL?.trim().replace(/\/$/, "") ?? "";
  if (!configured) return path;
  if (typeof window === "undefined") return `${configured}${path}`;
  try {
    const target = new URL(configured);
    if (target.hostname === window.location.hostname) return `${configured}${path}`;
  } catch {
    return path;
  }
  return path;
}

export function listMedicalSupplies(): Promise<MedicalSupply[]> {
  return apiRequest<MedicalSupply[]>(inventoryUrl("/inventory/products"), { method: "GET" }, { session: true });
}

export function readMedicalSupply(supplyId: number): Promise<MedicalSupply> {
  return apiRequest<MedicalSupply>(
    inventoryUrl(`/inventory/products/${supplyId}`),
    { method: "GET" },
    { session: true },
  );
}

const STOCK_KEYS = ["current_stock", "stock", "quantity_on_hand", "on_hand"] as const;

function stockRejection(
  route: string,
  method: "POST" | "PUT" | "PATCH",
  body: object,
  quantity: number,
): void {
  const record = body as Record<string, unknown>;
  const clinic = typeof record.clinic_id === "number" ? record.clinic_id : null;
  const product =
    typeof record.supply_id === "number"
      ? record.supply_id
      : typeof record.product_id === "number"
        ? record.product_id
        : null;
  track("direct_stock_edit_rejected", {
    attempted_method: method,
    attempted_route: route,
    rejection_reason: "stock_mutable_only_through_orders",
    quantity,
    clinic_id: clinic,
    country: clinic === null ? null : clinicCountry(clinic),
    product_id: product,
    product_category: typeof record.category === "string" ? briefingCategory(record.category) : null,
  });
}

function rejectDirectStockEdit(route: string, method: "POST" | "PUT" | "PATCH", body: object): void {
  const record = body as Record<string, unknown>;
  const forbidden = STOCK_KEYS.find((key) => Object.prototype.hasOwnProperty.call(record, key));
  if (!forbidden) return;
  const raw = record[forbidden];
  const quantity = typeof raw === "number" && Number.isInteger(raw) && raw >= 0 ? raw : 0;
  stockRejection(route, method, body, quantity);
  throw new ApiError("Stock is changed only through orders.", 403);
}

async function postInventory<T>(route: string, body: object): Promise<T> {
  rejectDirectStockEdit(route, "POST", body);
  try {
    return await apiRequest<T>(inventoryUrl(route), { method: "POST", body: JSON.stringify(body) }, { session: true });
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 403) stockRejection(route, "POST", body, 0);
    throw caught;
  }
}

export function createMedicalSupply(input: MedicalSupplyInput): Promise<MedicalSupply> {
  return postInventory<MedicalSupply>("/inventory/products", input);
}

export function createSupplyDelivery(input: SupplyDeliveryInput): Promise<SupplyDeliveryRecord> {
  return postInventory<SupplyDeliveryRecord>("/inventory/orders/inbound", input);
}

export function createSupplyConsumption(input: SupplyConsumptionInput): Promise<SupplyConsumptionRecord> {
  return postInventory<SupplyConsumptionRecord>("/inventory/orders/outbound", input);
}

type OrderListTask = {
  task_id: string;
  status: string;
  result: InventoryOrder[] | null;
};

export async function listInventoryOrders(): Promise<InventoryOrder[]> {
  const accepted = await apiRequest<{ task_id: string }>(
    inventoryUrl("/inventory/orders"),
    { method: "GET" },
    { session: true },
  );
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline) {
    const task = await apiRequest<OrderListTask>(
      inventoryUrl(`/tasks/${accepted.task_id}`),
      { method: "GET" },
      { session: true },
    );
    if (task.status === "success") return task.result ?? [];
    if (task.status === "failure") throw new ApiError("The order list could not be loaded.", 500);
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new ApiError("The order list is still running.", 504);
}
