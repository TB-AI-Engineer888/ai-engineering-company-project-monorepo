import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore — Healthcare that fits your life",
  description:
    "HealthCore is a network of 12 outpatient clinics across the US and UK offering same-day appointments, extended hours, and bilingual care.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
