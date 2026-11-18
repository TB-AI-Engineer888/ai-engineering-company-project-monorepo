"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type EventRow = { date: string; event_type: string; event_count: number };
type ErrorRow = { event_type: string; events: number; errors: number; error_rate: number };
type LatencyRow = { date: string; route_template: string; samples: number; mean_duration_ms: number };
type AuthRow = { date: string; failed: number; attempts: number; auth_failure_rate: number };

type Report = {
  period: { from: string; to: string };
  metrics: {
    events_per_day: EventRow[];
    error_rate_by_type: ErrorRow[];
    latency_per_day: LatencyRow[];
    auth_failure_rate: AuthRow[];
  };
};

function rateLabel(value: number) {
  return `${Math.round(value * 1000) / 10}%`;
}

export function TelemetryReport() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(start: string, end: string) {
    setLoading(true);
    setError(null);
    if ((start && !end) || (!start && end)) {
      setReport(null);
      setError("Choose both dates, or leave both empty for the last 7 days.");
      setLoading(false);
      return;
    }
    const params = new URLSearchParams();
    if (start && end) {
      const [year, month, day] = end.split("-").map(Number);
      const exclusiveEnd = new Date(Date.UTC(year, month - 1, day));
      exclusiveEnd.setUTCDate(exclusiveEnd.getUTCDate() + 1);
      const endDay = exclusiveEnd.toISOString().slice(0, 10);
      params.set("start_date", `${start}T00:00:00Z`);
      params.set("end_date", `${endDay}T00:00:00Z`);
    }
    const query = params.toString();
    try {
      const response = await fetch(query ? `/telemetry/report?${query}` : "/telemetry/report");
      const payload = (await response.json()) as Report & { error?: string };
      if (!response.ok) {
        setReport(null);
        setError(payload.error || `Report failed (${response.status})`);
        return;
      }
      setReport(payload);
    } catch {
      setReport(null);
      setError("The telemetry report could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load("", "");
  }, []);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">System telemetry</h2>
        <p className="mt-2 text-muted-foreground">
          Event volume, error rate, latency, and login failures for the engineering window.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Period</CardTitle>
          <CardDescription>
            {report
              ? `${report.period.from} to ${report.period.to}`
              : "The report defaults to the last 7 days in UTC."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              void load(startDate, endDate);
            }}
          >
            <div className="grid gap-1.5">
              <Label htmlFor="start-date">From</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="end-date">To</Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </div>
            <Button type="submit">Apply window</Button>
          </form>
        </CardContent>
      </Card>

      {loading ? <p className="text-sm text-muted-foreground">Loading the report…</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {report ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Events per day</CardTitle>
              <CardDescription>How many events of each type occurred on each day.</CardDescription>
            </CardHeader>
            <CardContent>
              {report.metrics.events_per_day.length === 0 ? (
                <p className="text-sm text-muted-foreground">No events in this window.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Event type</TableHead>
                      <TableHead>Count</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.metrics.events_per_day.map((row) => (
                      <TableRow key={`${row.date}-${row.event_type}`}>
                        <TableCell>{row.date}</TableCell>
                        <TableCell>{row.event_type}</TableCell>
                        <TableCell>{row.event_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Error rate by type</CardTitle>
              <CardDescription>Share of each event type that is an error or a failed write.</CardDescription>
            </CardHeader>
            <CardContent>
              {report.metrics.error_rate_by_type.length === 0 ? (
                <p className="text-sm text-muted-foreground">No events in this window.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Event type</TableHead>
                      <TableHead>Events</TableHead>
                      <TableHead>Errors</TableHead>
                      <TableHead>Error rate</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.metrics.error_rate_by_type.map((row) => (
                      <TableRow key={row.event_type}>
                        <TableCell>{row.event_type}</TableCell>
                        <TableCell>{row.events}</TableCell>
                        <TableCell>{row.errors}</TableCell>
                        <TableCell>{rateLabel(row.error_rate)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Latency per day</CardTitle>
              <CardDescription>Mean duration of recorded API routes, by day.</CardDescription>
            </CardHeader>
            <CardContent>
              {report.metrics.latency_per_day.length === 0 ? (
                <p className="text-sm text-muted-foreground">No latency samples in this window.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Route</TableHead>
                      <TableHead>Samples</TableHead>
                      <TableHead>Mean ms</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.metrics.latency_per_day.map((row) => (
                      <TableRow key={`${row.date}-${row.route_template}`}>
                        <TableCell>{row.date}</TableCell>
                        <TableCell>{row.route_template}</TableCell>
                        <TableCell>{row.samples}</TableCell>
                        <TableCell>{row.mean_duration_ms}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Login failure rate</CardTitle>
              <CardDescription>Failed login attempts divided by all login attempts, per day.</CardDescription>
            </CardHeader>
            <CardContent>
              {report.metrics.auth_failure_rate.length === 0 ? (
                <p className="text-sm text-muted-foreground">No login attempts in this window.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Failed</TableHead>
                      <TableHead>Attempts</TableHead>
                      <TableHead>Failure rate</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.metrics.auth_failure_rate.map((row) => (
                      <TableRow key={row.date}>
                        <TableCell>{row.date}</TableCell>
                        <TableCell>{row.failed}</TableCell>
                        <TableCell>{row.attempts}</TableCell>
                        <TableCell>{rateLabel(row.auth_failure_rate)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
