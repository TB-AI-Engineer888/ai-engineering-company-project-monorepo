import dynamic from "next/dynamic";

const IncidentAnalyzer = dynamic(
  () => import("@/components/incident-analyzer").then((mod) => mod.IncidentAnalyzer),
  {
    loading: () => (
      <p className="text-sm text-muted-foreground">Loading the incident analyzer…</p>
    ),
  },
);

export default function IncidentsPage() {
  return <IncidentAnalyzer />;
}
