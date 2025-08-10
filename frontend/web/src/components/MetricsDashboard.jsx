import { useEffect, useState } from "react";

export default function MetricsDashboard() {
  const [latency, setLatency] = useState(null);

  useEffect(() => {
    // demo: poll /health as a placeholder for metrics
    const t = setInterval(async () => {
      try {
        const r = await fetch("http://localhost:8000/health");
        setLatency(r.ok ? "OK" : "ERR");
      } catch {
        setLatency("ERR");
      }
    }, 2000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="card">
      <h3>Metrics</h3>
      <div className="row">
        <span>Backend:</span>
        <strong>{latency || "…"}</strong>
      </div>
      <p className="muted">
        Hook to /metrics Prometheus endpoint for real dashboards.
      </p>
    </div>
  );
}
