import { clearToken, getToken } from "@/lib/session";
import { ApiError, apiRequest } from "@/lib/http";
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
  let response: Response;
  try {
    response = await fetch("/api/incidents/results/export", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ApiError("We could not reach HealthCore. Check your connection and try again.", 0);
  }

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    throw new ApiError("Your session expired. Sign in again.", 401);
  }

  if (!response.ok) {
    let message = "The results file is not available yet. Analyse a CSV first, then try again.";
    try {
      const payload = (await response.json()) as { error?: unknown; detail?: unknown } | null;
      const raw = payload?.error ?? payload?.detail;
      if (typeof raw === "string" && raw.trim() && !/traceback|pat-\d|\b[1-5]\d\d\b/i.test(raw)) {
        message = raw.trim();
      }
    } catch {
      message = "The results file could not be downloaded. Try again, or contact HealthCore support.";
    }
    throw new ApiError(message, response.status);
  }

  let blob: Blob;
  try {
    blob = await response.blob();
  } catch {
    throw new ApiError("The results file could not be prepared. Try the download again.", response.status);
  }

  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = "results.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
