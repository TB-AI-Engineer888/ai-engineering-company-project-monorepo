"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/http";
import { readMonthlyClinicSupplyPerformance, type ClinicSupplyReport } from "@/lib/reporting";

const KPIS = [
  {
    name: "Supply Cost per Clinic",
    detail: "How much the clinic spent purchasing medical supplies this month.",
    read: (row: ClinicSupplyReport["clinics"][number]) =>
      `${row.total_supply_cost.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${row.currency}`,
  },
  {
    name: "Supply Consumption Volume",
    detail: "How many supply-consumption events the clinic recorded this month.",
    read: (row: ClinicSupplyReport["clinics"][number]) => String(row.supply_consumption_count),
  },
  {
    name: "Critical Stockout Frequency",
    detail: "How many times the clinic ran below the minimum supply threshold this month.",
    read: (row: ClinicSupplyReport["clinics"][number]) => String(row.critical_stockout_count),
  },
  {
    name: "Expiry Risk Count",
    detail: "How many supply batches were flagged as approaching expiry this month.",
    read: (row: ClinicSupplyReport["clinics"][number]) => String(row.expiry_risk_count),
  },
] as const;

function monthLabel(monthStart: string): string {
  const [year, month] = monthStart.split("-").map(Number);
  if (!year || !month) return monthStart;
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function ClinicSupplyReport() {
  const [report, setReport] = useState<ClinicSupplyReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    readMonthlyClinicSupplyPerformance()
      .then((body) => {
        if (active) setReport(body);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : "The monthly report could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Monthly Clinic Supply Performance Report</h2>
        <p className="mt-2 text-muted-foreground">
          For Dr. Okonkwo and Claire. US clinics are in USD and UK clinics are in GBP. The two currencies are shown side by side and are not added together.
        </p>
      </div>
      {loading ? <p className="text-sm text-muted-foreground">Loading the monthly report…</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {report && report.clinics.length === 0 ? (
        <p className="text-sm text-muted-foreground">No monthly clinic figures have been published yet.</p>
      ) : null}
      {report && report.clinics.length > 0 ? (
        <div className="space-y-8">
          <p className="text-sm font-medium">Month: {monthLabel(report.month_start)}</p>
          {KPIS.map((kpi) => (
            <section key={kpi.name} className="space-y-3">
              <div>
                <h3 className="text-lg font-semibold">{kpi.name}</h3>
                <p className="text-sm text-muted-foreground">{kpi.detail}</p>
              </div>
              <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
                <table className="w-full min-w-[32rem] text-left text-sm">
                  <thead className="bg-muted/50 text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">Clinic</th>
                      <th className="px-4 py-3 font-medium">Country</th>
                      <th className="px-4 py-3 font-medium">{kpi.name}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.clinics.map((row) => (
                      <tr key={`${kpi.name}-${row.clinic_id}`} className="border-t border-border">
                        <td className="px-4 py-3">Clinic {row.clinic_id}</td>
                        <td className="px-4 py-3">{row.country}</td>
                        <td className="px-4 py-3">{kpi.read(row)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
