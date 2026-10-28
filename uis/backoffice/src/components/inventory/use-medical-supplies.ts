"use client";

import { useEffect, useState } from "react";
import { listMedicalSupplies, type MedicalSupply } from "@/lib/inventory";

export function useMedicalSupplies() {
  const [supplies, setSupplies] = useState<MedicalSupply[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listMedicalSupplies()
      .then((rows) => {
        if (!cancelled) setSupplies(rows);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Could not load medical supplies.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { supplies, error, loading };
}
