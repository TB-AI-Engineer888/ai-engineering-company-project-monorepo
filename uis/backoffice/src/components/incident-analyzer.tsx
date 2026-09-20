"use client";

import { useState } from "react";
import { LoaderCircle } from "lucide-react";
import { AnalysisSummary } from "@/components/analysis-summary";
import { FileDropzone } from "@/components/file-dropzone";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { analyzeIncidents, downloadResultsCsv } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";

export function IncidentAnalyzer() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setFileName(file.name);
    setError(null);
    setExportError(null);
    setResult(null);
    setLoading(true);
    try {
      const next = await analyzeIncidents(file);
      setResult(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setExportError(null);
    setExporting(true);
    try {
      await downloadResultsCsv();
    } catch (caught) {
      setExportError(
        caught instanceof Error ? caught.message : "Could not download results.csv.",
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Incident analyzer</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground sm:text-base">
          Upload an incident CSV. Rows are validated against clinic codes,
          country, category, description, and closed-case scores. The summary
          shows volume, category, status, country, and satisfaction. Patient
          identifiers are not displayed.
        </p>
      </div>

      <FileDropzone disabled={loading} onFile={handleFile} />
      <p className="flex flex-col gap-2 text-sm sm:flex-row sm:gap-6">
        <a href="/api/incidents/sample" className="underline underline-offset-4">
          Download sample CSV
        </a>
        <a
          href="/api/incidents/project.zip"
          className="font-medium underline underline-offset-4"
        >
          Download analyzer zip
        </a>
      </p>

      {fileName && (
        <p className="text-sm text-muted-foreground">
          Selected file: <span className="font-mono text-foreground">{fileName}</span>
        </p>
      )}

      {loading && (
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm">
          <LoaderCircle className="size-4 animate-spin" />
          Reading the file and calculating metrics. Invalid rows are counted, not ignored.
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTitle>The file could not be analysed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {exportError && (
        <Alert variant="destructive">
          <AlertTitle>CSV export failed</AlertTitle>
          <AlertDescription>{exportError}</AlertDescription>
        </Alert>
      )}

      {!loading && !error && !result && (
        <div className="rounded-xl border border-border bg-card px-5 py-8 text-sm text-muted-foreground">
          No analysis yet. Upload a CSV to see the summary.
        </div>
      )}

      {result && (
        <AnalysisSummary result={result} exporting={exporting} onExport={handleExport} />
      )}
    </div>
  );
}
