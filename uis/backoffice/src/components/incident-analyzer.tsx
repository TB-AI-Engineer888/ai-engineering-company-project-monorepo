"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { LoaderCircle } from "lucide-react";
import { AnalysisSummary } from "@/components/analysis-summary";
import { FileDropzone } from "@/components/file-dropzone";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { analyzeIncidents, downloadResultsCsv } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";

function readableError(caught: unknown, fallback: string): string {
  if (!(caught instanceof Error)) return fallback;
  const message = caught.message?.trim();
  if (!message || /unexpected token|traceback|request failed|\b[1-5]\d\d\b/i.test(message)) {
    return fallback;
  }
  return message;
}

export function IncidentAnalyzer() {
  const selectedFile = useRef<File | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function handleFile(file: File) {
    selectedFile.current = file;
    setFileName(file.name);
    setError(null);
    setExportError(null);
    setResult(null);
    setLoading(true);
    try {
      const next = await analyzeIncidents(file);
      setResult(next);
    } catch (caught) {
      setResult(null);
      setError(readableError(caught, "The file could not be analysed. Try again, or contact HealthCore support."));
    } finally {
      setLoading(false);
    }
  }

  function retryAnalysis() {
    const file = selectedFile.current;
    if (!file || loading) return;
    void handleFile(file);
  }

  async function handleExport() {
    setExportError(null);
    setExporting(true);
    try {
      await downloadResultsCsv();
    } catch (caught) {
      setExportError(
        readableError(caught, "The results file could not be downloaded. Try again, or contact HealthCore support."),
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Incident analyzer</h2>
      </div>

      <FileDropzone disabled={loading} onFile={handleFile} />

      {fileName && (
        <p className="text-sm text-muted-foreground">
          Selected file: <span className="font-mono text-foreground">{fileName}</span>
        </p>
      )}

      {loading && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm">
          <LoaderCircle className="size-4 animate-spin" />
          Analysing file…
        </div>
      )}

      {!loading && error && (
        <Alert variant="destructive">
          <AlertTitle>The file could not be analysed</AlertTitle>
          <AlertDescription>
            <p>{error}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" onClick={retryAnalysis} disabled={!fileName || loading}>
                Try again
              </Button>
              <Link href="/" className="underline underline-offset-4">
                Back to operations overview
              </Link>
            </div>
            <p className="mt-2">If this keeps happening, contact HealthCore support.</p>
          </AlertDescription>
        </Alert>
      )}

      {exportError && (
        <Alert variant="destructive">
          <AlertTitle>CSV export failed</AlertTitle>
          <AlertDescription>
            <p>{exportError}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" onClick={() => void handleExport()} disabled={exporting}>
                {exporting ? "Preparing CSV…" : "Try the download again"}
              </Button>
              <Link href="/" className="underline underline-offset-4">
                Back to operations overview
              </Link>
            </div>
            <p className="mt-2">If this keeps happening, contact HealthCore support.</p>
          </AlertDescription>
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
