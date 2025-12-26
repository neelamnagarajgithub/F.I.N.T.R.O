"use client";

import { useState } from "react";
import DashboardPageLayout from "@/components/dashboard/layout";
import DashboardCard from "@/components/dashboard/card";
import DashboardChart from "@/components/dashboard/chart";
import BracketsIcon from "@/components/icons/brackets";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Bullet } from "@/components/ui/bullet";

const API_BASE =  "https://cfo-backend-883163069340.us-central1.run.app";

const defaultInstructions = [
  "delay collections by 15 days",
  "add ₹5Cr order on 2025-12-25",
  "defer rent 10 days",
];

export default function SimulatorPage() {
  const [orgId, setOrgId] = useState("315");
  const [instructionsText, setInstructionsText] = useState(defaultInstructions.join("\n"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  async function runScenario() {
    setLoading(true);
    setError(null);
    setResult(null);

    const instructions = instructionsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const res = await fetch(`${API_BASE}/api/org/${encodeURIComponent(orgId)}/scenario`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scenario_instructions: instructions,
          base_url: typeof window !== "undefined" ? window.location.origin : "http://localhost:3000",
        }),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`Request failed (${res.status}) ${text}`);
      }

      const json = await res.json();
      setResult(json);
    } catch (err: any) {
      setError(err?.message ?? String(err));
    } finally {
      setLoading(false);
    }
  }

  function downloadHtmlReport() {
    if (!result?.html_report) return;
    const html = result.html_report;
    const filename = `scenario-report-org-${orgId}.html`;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function openReportInNewTab() {
    if (!result?.html_report) return;
    const blob = new Blob([result.html_report], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    // Note: URL revoked later by browser lifecycle or you can revoke after small timeout
    setTimeout(() => URL.revokeObjectURL(url), 1000 * 30);
  }

  return (
    <DashboardPageLayout
      header={{
        title: "Scenario Simulator",
        description: "What-if analysis",
        icon: BracketsIcon,
      }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <DashboardCard title="SCENARIO INPUTS" intent="default">
          <div className="space-y-4">
            <div>
              <Label htmlFor="orgId" className="text-xs uppercase text-muted-foreground">
                Org ID
              </Label>
              <Input id="orgId" value={orgId} onChange={(e) => setOrgId(e.target.value)} className="mt-2" />
            </div>

            <div>
              <Label htmlFor="instructions" className="text-xs uppercase text-muted-foreground">
                Scenario Instructions (one per line)
              </Label>
              <textarea
                id="instructions"
                value={instructionsText}
                onChange={(e) => setInstructionsText(e.target.value)}
                className="w-full mt-2 p-2 bg-transparent border rounded-md min-h-[120px] resize-none"
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={runScenario} disabled={loading} className="flex-1">
                {loading ? "Running..." : "Run Simulation"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setInstructionsText(defaultInstructions.join("\n"));
                }}
              >
                Reset
              </Button>
            </div>

            {error && <p className="text-sm text-destructive">Error: {error}</p>}
          </div>
        </DashboardCard>

        <DashboardCard title="BASE CASE vs SCENARIO" intent="default">
          <div className="space-y-4">
            {result ? (
              <>
                <div className="grid grid-cols-2 gap-4 p-3 bg-accent rounded-md">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase mb-1">Base Case Min Balance</p>
                    <p className="text-2xl font-display">
                      {result.base_forecast?.summary?.min_balance
                        ? `₹${Number(result.base_forecast.summary.min_balance).toLocaleString("en-IN")}`
                        : "—"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Min Balance</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase mb-1">Scenario Min Balance</p>
                    <p className="text-2xl font-display text-success">
                      {result.scenario_forecast?.summary?.min_balance
                        ? `₹${Number(result.scenario_forecast.summary.min_balance).toLocaleString("en-IN")}`
                        : "—"}
                    </p>
                    <p className="text-xs text-success mt-1">
                      {result.impact?.min_balance_improvement != null
                        ? `${Number(result.impact.min_balance_improvement).toLocaleString("en-IN", {
                            style: "currency",
                            currency: "INR",
                            maximumFractionDigits: 0,
                          })}`
                        : ""}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button onClick={downloadHtmlReport} disabled={!result.html_report}>
                    Download HTML Report
                  </Button>
                  <Button variant="outline" onClick={openReportInNewTab} disabled={!result.html_report}>
                    Open Report
                  </Button>
                  {result.pdf_url && (
                    <a href={result.pdf_url} target="_blank" rel="noreferrer">
                      <Button variant="ghost">Open PDF</Button>
                    </a>
                  )}
                </div>

                <div className="mt-4">
                  <h4 className="text-sm uppercase text-muted-foreground mb-2">Impact Summary</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-3 bg-accent rounded">
                      <p className="text-xs text-muted-foreground uppercase">Min Balance (base)</p>
                      <p className="text-lg font-display">
                        {result.base_forecast?.summary?.min_balance
                          ? `₹${Number(result.base_forecast.summary.min_balance).toLocaleString("en-IN")}`
                          : "—"}
                      </p>
                    </div>
                    <div className="p-3 bg-accent rounded">
                      <p className="text-xs text-muted-foreground uppercase">Min Balance (scenario)</p>
                      <p className="text-lg font-display">
                        {result.scenario_forecast?.summary?.min_balance
                          ? `₹${Number(result.scenario_forecast.summary.min_balance).toLocaleString("en-IN")}`
                          : "—"}
                      </p>
                    </div>
                    <div className="p-3 bg-accent rounded">
                      <p className="text-xs text-muted-foreground uppercase">Total Net Delta</p>
                      <p className="text-lg font-display">
                        {result.impact?.total_net_delta != null
                          ? `₹${Number(result.impact.total_net_delta).toLocaleString("en-IN")}`
                          : "—"}
                      </p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Run a scenario to see results here.</p>
            )}
          </div>
        </DashboardCard>
      </div>

      <div className="mb-6">
        <DashboardChart />
      </div>

      <DashboardCard title="SENSITIVITY ANALYSIS" intent="default">
        <div className="space-y-3">
          {result?.sensitivity?.length ? (
            result.sensitivity.map((item: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 bg-accent rounded-md">
                <div className="flex items-center gap-3 flex-1">
                  <Bullet
                    variant={item.improvement > 0 ? "success" : item.improvement < 0 ? "destructive" : "default"}
                  />
                  <p className="text-sm">{`${item.lever} = ${item.value}`}</p>
                </div>
                <Badge className="text-xs">{item.improvement ? `${item.improvement}` : "—"}</Badge>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No sensitivity data yet.</p>
          )}
        </div>
      </DashboardCard>
    </DashboardPageLayout>
  );
}