import { buildTelemetryEvent, routeTemplate, scrubMessage, sectionForPath } from "../src/services/telemetry-catalogue";
import { clinicCountry, clinicStock, daysUntilExpiry, thresholdBand } from "../src/services/inventory-events";
import { resetTelemetryForTests, track } from "../src/services/telemetry";

const context = {
  sessionId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  userId: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  now: "2026-11-18T12:00:00.000Z",
  eventId: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  requestId: "dddddddd-dddd-dddd-dddd-dddddddddddd",
};

beforeEach(() => {
  resetTelemetryForTests();
  process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT = "http://127.0.0.1:9/telemetry/events";
});

test("login_failed forces an empty user and session", () => {
  const event = buildTelemetryEvent("login_failed", { failure_reason: "bad_password", email: "a@b.c" }, context);
  expect(event?.userId).toBeNull();
  expect(event?.sessionId).toBeNull();
  expect(event?.properties).toEqual({ failure_reason: "bad_password" });
});

test("a property outside the allowlist is dropped", () => {
  const event = buildTelemetryEvent("login_succeeded", { role: "user", email: "a@b.c" }, context);
  expect(event?.properties).toEqual({ role: "user" });
});

test("account_registered keeps the staff id and clears the session", () => {
  const event = buildTelemetryEvent("account_registered", { role: "user" }, context);
  expect(event?.userId).toBe(context.userId);
  expect(event?.sessionId).toBeNull();
});

test("scrubber removes emails and long digit runs", () => {
  expect(scrubMessage("Failed for ada@healthcore.test record 1234567")).toBe(
    "Failed for [redacted] record [redacted]",
  );
});

test("section names follow the backoffice routes", () => {
  expect(sectionForPath("/backoffice/inventory/orders/inbound")).toBe("inventory_inbound");
  expect(sectionForPath("/incidents")).toBe("incidents");
  expect(routeTemplate("/inventory/products/15")).toBe("/inventory/products/{id}");
});

test("clinic stock and threshold use the clinic directory", () => {
  expect(clinicCountry(3)).toBe("US");
  expect(clinicCountry(11)).toBe("UK");
  const orders = [
    { order_kind: "inbound", clinic_id: 3, supply_id: 1, quantity: 12 },
    { order_kind: "outbound", clinic_id: 3, supply_id: 1, quantity: 4 },
    { order_kind: "inbound", clinic_id: 1, supply_id: 1, quantity: 40 },
  ];
  expect(clinicStock(orders, 3, 1)).toBe(8);
  expect(thresholdBand(12, 0)).toBe("out");
  expect(thresholdBand(12, 4)).toBe("low");
  expect(thresholdBand(4, 2)).toBeNull();
  expect(daysUntilExpiry("2026-11-20", new Date("2026-11-18T15:00:00.000Z"))).toBe(2);
});

test("twenty events flush as one batch and a failed batch is discarded", async () => {
  const bodies: string[] = [];
  let attempts = 0;
  const fetchMock = jest.fn(async (_url: string, init?: RequestInit) => {
    attempts += 1;
    if (attempts < 3) throw new Error("down");
    bodies.push(String(init?.body));
    return { ok: true } as Response;
  });
  global.fetch = fetchMock as typeof fetch;
  Object.defineProperty(global, "window", {
    configurable: true,
    value: {
      localStorage: { getItem: () => null, setItem: () => undefined, removeItem: () => undefined },
      sessionStorage: { getItem: () => null, setItem: () => undefined, removeItem: () => undefined },
      location: { pathname: "/login" },
      addEventListener: () => undefined,
    },
  });
  Object.defineProperty(global, "document", {
    configurable: true,
    value: { visibilityState: "visible", addEventListener: () => undefined },
  });
  Object.defineProperty(global, "crypto", {
    configurable: true,
    value: { randomUUID: () => "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee" },
  });

  for (let index = 0; index < 20; index += 1) {
    track("login_failed", { failure_reason: "unknown_user" });
  }
  await new Promise((resolve) => setTimeout(resolve, 2000));
  expect(attempts).toBe(3);
  expect(bodies).toHaveLength(1);
  const batch = JSON.parse(bodies[0]) as { events: { event_type: string; sessionId: null }[] };
  expect(batch.events).toHaveLength(20);
  expect(batch.events[0].event_type).toBe("login_failed");
  expect(batch.events[0].sessionId).toBeNull();
});
