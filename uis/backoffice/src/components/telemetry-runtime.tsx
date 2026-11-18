"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useReportWebVitals } from "next/web-vitals";
import { sectionForPath } from "@/services/telemetry-catalogue";
import { track } from "@/services/telemetry";

export function TelemetryRuntime() {
  const pathname = usePathname();
  const previous = useRef<string | null>(null);

  useEffect(() => {
    const section = sectionForPath(pathname);
    const prior = previous.current;
    const timer = window.setTimeout(() => {
      track("backoffice_section_viewed", {
        section,
        previous_section: prior,
      });
      previous.current = section;
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [pathname]);

  useReportWebVitals((metric) => {
    if (metric.rating !== "good" && metric.rating !== "needs-improvement" && metric.rating !== "poor") return;
    if (typeof metric.value !== "number" || metric.value < 0) return;
    track("web_vital_recorded", {
      metric_name: metric.name,
      value: metric.value,
      rating: metric.rating,
      section: sectionForPath(window.location.pathname),
    });
  });

  return null;
}
