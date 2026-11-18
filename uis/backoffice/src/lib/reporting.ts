import { apiRequest } from "@/lib/http";

export type ClinicSupplyRow = {
  clinic_id: string;
  country: string;
  total_supply_cost: number;
  supply_consumption_count: number;
  critical_stockout_count: number;
  expiry_risk_count: number;
  currency: string;
};

export type ClinicSupplyReport = {
  month_start: string;
  clinics: ClinicSupplyRow[];
};

export function readMonthlyClinicSupplyPerformance(monthStart?: string): Promise<ClinicSupplyReport> {
  const query = monthStart ? `?month_start=${encodeURIComponent(monthStart)}` : "";
  return apiRequest<ClinicSupplyReport>(
    `/reporting/monthly-clinic-supply-performance${query}`,
    { method: "GET" },
    { session: true },
  );
}
