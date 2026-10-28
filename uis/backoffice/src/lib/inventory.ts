import { apiRequest } from "@/lib/http";

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

export function createSupplyDelivery(input: SupplyDeliveryInput): Promise<SupplyDeliveryRecord> {
  return apiRequest<SupplyDeliveryRecord>(
    inventoryUrl("/inventory/orders/inbound"),
    { method: "POST", body: JSON.stringify(input) },
    { session: true },
  );
}

export function createSupplyConsumption(input: SupplyConsumptionInput): Promise<SupplyConsumptionRecord> {
  return apiRequest<SupplyConsumptionRecord>(
    inventoryUrl("/inventory/orders/outbound"),
    { method: "POST", body: JSON.stringify(input) },
    { session: true },
  );
}

export function listInventoryOrders(): Promise<InventoryOrder[]> {
  return apiRequest<InventoryOrder[]>(inventoryUrl("/inventory/orders"), { method: "GET" }, { session: true });
}
