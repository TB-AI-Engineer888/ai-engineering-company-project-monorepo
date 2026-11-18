export const SCHEMA_VERSION = 1;

const UUID = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
const ROUTE = /^\/[A-Za-z0-9_./{}-]{0,119}$/;
const SKU = /^[A-Za-z0-9._-]{1,40}$/;
const VENDOR = /^[A-Za-z0-9][A-Za-z0-9 .,&'()-]{0,119}$/;
const LOT = /^[A-Za-z0-9._-]{1,40}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ERROR_NAME = /^[A-Za-z][A-Za-z0-9_]{0,79}$/;

export const SECTIONS = [
  "home",
  "login",
  "register",
  "account_profile",
  "inventory_products",
  "inventory_orders",
  "inventory_inbound",
  "inventory_outbound",
  "incidents",
] as const;

const CATEGORIES = ["medication", "ppe", "consumable", "equipment"] as const;
const COUNTRIES = ["US", "UK"] as const;
const UNITS = ["box", "unit", "pack", "vial"] as const;
const DEPARTMENTS = ["primary_care", "specialty_care", "chronic_care", "general_consultation"] as const;

type Check = (value: unknown) => boolean;
type Identity = "required" | "null" | "optional";

type EventSpec = {
  required: string[];
  fields: Record<string, Check>;
  userId: Identity;
  sessionId: Identity;
};

export type TelemetryContext = {
  sessionId: string | null;
  userId: string | null;
  now: string;
  eventId: string;
  requestId: string;
};

export type WireEvent = {
  eventId: string;
  timestamp: string;
  sessionId: string | null;
  userId: string | null;
  event_type: string;
  schemaVersion: number;
  requestId: string;
  properties: Record<string, unknown>;
};

function oneOf(values: readonly string[]): Check {
  return (value) => typeof value === "string" && values.includes(value);
}

function integer(min: number, max?: number): Check {
  return (value) =>
    typeof value === "number" &&
    Number.isInteger(value) &&
    value >= min &&
    (max === undefined || value <= max);
}

function nullable(check: Check): Check {
  return (value) => value === null || check(value);
}

function text(pattern: RegExp, max: number): Check {
  return (value) => typeof value === "string" && value.length <= max && pattern.test(value);
}

const clinicId = integer(1, 12);
const country = oneOf(COUNTRIES);
const category = oneOf(CATEGORIES);
const productId = integer(1);
const section = oneOf(SECTIONS);
const route = text(ROUTE, 120);

const inventoryCore: Record<string, Check> = {
  clinic_id: clinicId,
  country,
  product_id: productId,
  product_category: category,
};

const catalogue: Record<string, EventSpec> = {
  inbound_order_created: {
    userId: "required",
    sessionId: "required",
    required: [
      "clinic_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "order_id",
      "vendor_name",
      "sku",
      "unit",
      "country_mismatch",
      "total_cost",
    ],
    fields: {
      ...inventoryCore,
      quantity: integer(1),
      order_id: integer(1),
      vendor_name: text(VENDOR, 120),
      sku: text(SKU, 40),
      unit: oneOf(UNITS),
      country_mismatch: (value) => typeof value === "boolean",
      total_cost: (value) => typeof value === "number" && Number.isFinite(value) && value >= 0,
    },
  },
  outbound_order_created: {
    userId: "required",
    sessionId: "required",
    required: [
      "clinic_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "department",
      "order_id",
      "consumption_type",
      "sku",
      "clinic_stock_after",
      "global_stock_after",
    ],
    fields: {
      ...inventoryCore,
      quantity: integer(1),
      department: oneOf(DEPARTMENTS),
      order_id: integer(1),
      consumption_type: oneOf(["clinical_use", "expiry_waste"]),
      sku: text(SKU, 40),
      clinic_stock_after: integer(0),
      global_stock_after: integer(0),
    },
  },
  stock_threshold_triggered: {
    userId: "required",
    sessionId: "required",
    required: [
      "clinic_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "threshold_quantity",
      "band",
      "stock_before",
      "trigger_order_id",
      "trigger_order_kind",
    ],
    fields: {
      ...inventoryCore,
      quantity: integer(0),
      threshold_quantity: integer(0),
      band: oneOf(["low", "out"]),
      stock_before: integer(0),
      trigger_order_id: integer(1),
      trigger_order_kind: (value) => value === "outbound",
    },
  },
  direct_stock_edit_rejected: {
    userId: "optional",
    sessionId: "optional",
    required: [
      "attempted_method",
      "attempted_route",
      "rejection_reason",
      "quantity",
      "clinic_id",
      "country",
      "product_id",
      "product_category",
    ],
    fields: {
      attempted_method: oneOf(["POST", "PUT", "PATCH"]),
      attempted_route: route,
      rejection_reason: (value) => value === "stock_mutable_only_through_orders",
      quantity: integer(0),
      clinic_id: nullable(clinicId),
      country: nullable(country),
      product_id: nullable(productId),
      product_category: nullable(category),
    },
  },
  supply_expiry_flagged: {
    userId: "required",
    sessionId: "required",
    required: [
      "clinic_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "lot_id",
      "expires_on",
      "days_to_expiry",
      "trigger",
    ],
    fields: {
      ...inventoryCore,
      quantity: integer(0),
      lot_id: text(LOT, 40),
      expires_on: text(DATE, 10),
      days_to_expiry: integer(-3650, 30),
      trigger: oneOf(["receipt", "daily_sweep"]),
    },
  },
  product_registered: {
    userId: "required",
    sessionId: "required",
    required: ["product_id", "sku", "product_category", "unit", "country", "quantity"],
    fields: {
      product_id: productId,
      sku: text(SKU, 40),
      product_category: category,
      unit: oneOf(UNITS),
      country,
      quantity: (value) => value === 0,
    },
  },
  incident_analysis_completed: {
    userId: "optional",
    sessionId: "optional",
    required: ["source_kind", "row_count", "duration_ms"],
    fields: {
      source_kind: oneOf(["upload", "sample"]),
      row_count: integer(0),
      duration_ms: (value) => typeof value === "number" && Number.isFinite(value) && value >= 0,
    },
  },
  login_succeeded: {
    userId: "required",
    sessionId: "required",
    required: ["role"],
    fields: { role: oneOf(["admin", "manager", "user"]) },
  },
  login_failed: {
    userId: "null",
    sessionId: "null",
    required: ["failure_reason"],
    fields: { failure_reason: oneOf(["unknown_user", "bad_password", "inactive_user"]) },
  },
  session_expired: {
    userId: "optional",
    sessionId: "required",
    required: ["reason"],
    fields: { reason: oneOf(["token_expired", "inactive_user"]) },
  },
  account_registered: {
    userId: "required",
    sessionId: "null",
    required: ["role"],
    fields: { role: (value) => value === "user" },
  },
  outbound_order_rejected: {
    userId: "required",
    sessionId: "required",
    required: [
      "clinic_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "department",
      "available_global",
      "rejection_reason",
    ],
    fields: {
      ...inventoryCore,
      quantity: integer(1),
      department: oneOf(DEPARTMENTS),
      available_global: integer(0),
      rejection_reason: (value) => value === "insufficient_stock",
    },
  },
  inventory_validation_failed: {
    userId: "optional",
    sessionId: "optional",
    required: ["route_template", "method", "http_status", "reason_code", "field_name"],
    fields: {
      route_template: route,
      method: (value) => value === "POST",
      http_status: integer(400, 422),
      reason_code: oneOf([
        "duplicate_sku",
        "unknown_product",
        "invalid_quantity",
        "invalid_clinic",
        "invalid_category",
        "invalid_country",
        "invalid_consumption_type",
        "invalid_department",
        "invalid_body",
      ]),
      field_name: nullable(
        oneOf([
          "sku",
          "quantity",
          "clinic_id",
          "supply_id",
          "category",
          "country",
          "consumption_type",
          "vendor_name",
          "department",
          "unit",
          "name",
        ]),
      ),
    },
  },
  client_exception_captured: {
    userId: "optional",
    sessionId: "optional",
    required: ["section", "error_name", "message_scrubbed"],
    fields: {
      section,
      error_name: text(ERROR_NAME, 80),
      message_scrubbed: (value) => typeof value === "string" && value.length <= 200,
    },
  },
  api_latency_recorded: {
    userId: "optional",
    sessionId: "optional",
    required: ["method", "route_template", "status_code", "duration_ms", "slow"],
    fields: {
      method: oneOf(["GET", "POST", "PUT", "PATCH", "DELETE"]),
      route_template: route,
      status_code: integer(100, 599),
      duration_ms: (value) => typeof value === "number" && Number.isFinite(value) && value >= 0,
      slow: (value) => typeof value === "boolean",
    },
  },
  backoffice_section_viewed: {
    userId: "optional",
    sessionId: "optional",
    required: ["section", "previous_section"],
    fields: {
      section,
      previous_section: nullable(section),
    },
  },
  backoffice_flow_abandoned: {
    userId: "optional",
    sessionId: "optional",
    required: ["flow", "last_completed_step", "time_on_form_seconds"],
    fields: {
      flow: oneOf(["inbound_order", "outbound_order"]),
      last_completed_step: oneOf(["none", "supply", "quantity", "vendor", "consumption_type", "clinic"]),
      time_on_form_seconds: integer(2, 86400),
    },
  },
  web_vital_recorded: {
    userId: "optional",
    sessionId: "optional",
    required: ["metric_name", "value", "rating", "section"],
    fields: {
      metric_name: (value) => typeof value === "string" && value.length > 0 && value.length <= 40,
      value: (value) => typeof value === "number" && Number.isFinite(value) && value >= 0,
      rating: oneOf(["good", "needs-improvement", "poor"]),
      section,
    },
  },
};

function identity(rule: Identity, value: string | null): string | null | undefined {
  if (rule === "null") return null;
  const valid = value !== null && UUID.test(value) ? value : null;
  if (rule === "required") return valid ?? undefined;
  return valid;
}

export function buildTelemetryEvent(
  eventType: string,
  input: Record<string, unknown>,
  context: TelemetryContext,
): WireEvent | null {
  const spec = catalogue[eventType];
  if (!spec) return null;
  if (!UUID.test(context.eventId) || !UUID.test(context.requestId)) return null;
  const userId = identity(spec.userId, context.userId);
  const sessionId = identity(spec.sessionId, context.sessionId);
  if (userId === undefined || sessionId === undefined) return null;

  const properties: Record<string, unknown> = {};
  for (const key of spec.required) {
    if (!spec.fields[key](input[key])) return null;
    properties[key] = input[key];
  }
  return {
    eventId: context.eventId,
    timestamp: context.now,
    sessionId,
    userId,
    event_type: eventType,
    schemaVersion: SCHEMA_VERSION,
    requestId: context.requestId,
    properties,
  };
}

export function scrubMessage(message: string): string {
  return message
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[redacted]")
    .replace(/\d{6,}/g, "[redacted]")
    .slice(0, 200);
}

export function sectionForPath(pathname: string): (typeof SECTIONS)[number] {
  if (pathname === "/login") return "login";
  if (pathname === "/register") return "register";
  if (pathname.startsWith("/account")) return "account_profile";
  if (pathname.startsWith("/backoffice/inventory/orders/inbound")) return "inventory_inbound";
  if (pathname.startsWith("/backoffice/inventory/orders/outbound")) return "inventory_outbound";
  if (pathname.startsWith("/backoffice/inventory/orders")) return "inventory_orders";
  if (pathname.startsWith("/backoffice/inventory/products")) return "inventory_products";
  if (pathname.startsWith("/incidents")) return "incidents";
  return "home";
}

export function routeTemplate(path: string): string {
  let pathname = path.split("?")[0] ?? path;
  if (pathname.startsWith("http://") || pathname.startsWith("https://")) {
    try {
      pathname = new URL(pathname).pathname;
    } catch {
      pathname = path.split("?")[0] ?? path;
    }
  }
  return pathname.replace(/\/\d+(?=\/|$)/g, "/{id}").slice(0, 120);
}
