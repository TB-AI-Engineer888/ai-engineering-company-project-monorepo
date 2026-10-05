import { clearToken, getToken } from "@/lib/session";
import { apiRequest } from "@/lib/http";
import type { AnalysisResult } from "@/lib/types";

export async function analyzeIncidents(file: File): Promise<AnalysisResult> {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<AnalysisResult>(
    "/api/incidents/analyze",
    { method: "POST", body },
    { session: true },
  );
}

export async function downloadResultsCsv(): Promise<void> {
  const token = getToken();
  const response = await fetch("/api/incidents/results/export", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    throw new Error("Your session expired. Sign in again.");
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { error?: string; detail?: string };
      message = payload.error || payload.detail || message;
    } catch {
      message = `Request failed (${response.status})`;
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "results.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
