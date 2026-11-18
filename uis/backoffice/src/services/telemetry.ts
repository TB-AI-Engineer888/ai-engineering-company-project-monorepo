import { getSessionId, getStaffId } from "@/lib/session";
import {
  buildTelemetryEvent,
  routeTemplate,
  scrubMessage,
  sectionForPath,
  type WireEvent,
} from "@/services/telemetry-catalogue";

const BATCH_SIZE = 20;
const FLUSH_MS = 10_000;
const MAX_ATTEMPTS = 3;
const BACKOFF_MS = 250;

let queue: WireEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let flushing = false;
let lifecycleInstalled = false;
const recentErrors = new Map<string, number>();

function endpoint(): string {
  return process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT?.trim() ?? "";
}

function uuid(): string {
  return crypto.randomUUID();
}

export function track(eventType: string, properties: Record<string, unknown>): void {
  if (typeof window === "undefined") return;
  installTelemetryLifecycle();
  const event = buildTelemetryEvent(eventType, properties, {
    sessionId: getSessionId(),
    userId: getStaffId(),
    now: new Date().toISOString(),
    eventId: uuid(),
    requestId: uuid(),
  });
  if (!event) return;
  queue.push(event);
  if (queue.length >= BATCH_SIZE) {
    void flush(false);
    return;
  }
  if (timer === null) {
    timer = setTimeout(() => {
      timer = null;
      void flush(false);
    }, FLUSH_MS);
  }
}

function installTelemetryLifecycle(): void {
  if (lifecycleInstalled || typeof window === "undefined" || typeof document === "undefined") return;
  lifecycleInstalled = true;
  window.addEventListener("error", (event) => {
    const error = event.error;
    const name = error instanceof Error ? error.name : "Error";
    captureException(name, event.message || (error instanceof Error ? error.message : ""));
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const name = reason instanceof Error ? reason.name : "UnhandledRejection";
    const message = reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "";
    captureException(name, message);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flushWithBeacon();
  });
}

function captureException(name: string, message: string): void {
  const section = sectionForPath(window.location.pathname);
  const errorName = /^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(name) ? name : "Error";
  const key = `${section}:${errorName}`;
  const now = Date.now();
  const previous = recentErrors.get(key) ?? 0;
  if (now - previous < 60_000) return;
  recentErrors.set(key, now);
  track("client_exception_captured", {
    section,
    error_name: errorName,
    message_scrubbed: scrubMessage(message),
  });
}

function takeQueue(): WireEvent[] {
  if (timer !== null) {
    clearTimeout(timer);
    timer = null;
  }
  const batch = queue;
  queue = [];
  return batch;
}

async function flush(fromBeacon: boolean): Promise<void> {
  if (flushing || queue.length === 0) return;
  const batch = takeQueue();
  if (fromBeacon) {
    deliverBeacon(batch);
    return;
  }
  flushing = true;
  try {
    const delivered = await sendWithRetry(batch);
    if (!delivered) return;
  } finally {
    flushing = false;
  }
  if (queue.length >= BATCH_SIZE) void flush(false);
}

function flushWithBeacon(): void {
  if (queue.length === 0) return;
  const batch = takeQueue();
  const accepted = deliverBeacon(batch);
  if (!accepted) queue = batch.concat(queue);
}

function deliverBeacon(batch: WireEvent[]): boolean {
  const url = endpoint();
  if (!url || typeof navigator === "undefined" || typeof navigator.sendBeacon !== "function") return false;
  const body = new Blob([JSON.stringify({ events: batch })], { type: "application/json" });
  return navigator.sendBeacon(url, body);
}

async function sendWithRetry(batch: WireEvent[]): Promise<boolean> {
  const url = endpoint();
  if (!url) return false;
  let wait = BACKOFF_MS;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events: batch }),
        keepalive: true,
      });
      if (response.ok) return true;
    } catch {
      // The next attempt waits. After the last attempt the batch is discarded.
    }
    if (attempt < MAX_ATTEMPTS) {
      await new Promise((resolve) => setTimeout(resolve, wait));
      wait *= 2;
    }
  }
  return false;
}

export function recordLatency(path: string, method: string, status: number, startedAt: number): void {
  if (path.includes("/telemetry/")) return;
  const duration = Math.max(0, Math.round(performance.now() - startedAt));
  const slow = duration >= 500;
  if (!slow && Math.random() >= 0.05) return;
  const normalized = method.toUpperCase();
  if (!["GET", "POST", "PUT", "PATCH", "DELETE"].includes(normalized)) return;
  track("api_latency_recorded", {
    method: normalized,
    route_template: routeTemplate(path),
    status_code: status,
    duration_ms: duration,
    slow,
  });
}

export function resetTelemetryForTests(): void {
  queue = [];
  if (timer !== null) clearTimeout(timer);
  timer = null;
  flushing = false;
  lifecycleInstalled = false;
  recentErrors.clear();
}
