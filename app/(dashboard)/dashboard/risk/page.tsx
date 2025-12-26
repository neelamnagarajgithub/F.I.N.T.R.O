import DashboardPageLayout from "@/components/dashboard/layout";
import DashboardCard from "@/components/dashboard/card";
import DashboardStat from "@/components/dashboard/stat";
import AlertIcon from "@/components/icons/alert";
import { Badge } from "@/components/ui/badge";
import { Bullet } from "@/components/ui/bullet";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "https://cfo-backend-883163069340.us-central1.run.app";

/**
 * Small helpers
 */
function fmtNumber(value: number | string | undefined) {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function fmtCurrency(value: number | string | undefined) {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  // Using INR formatting used elsewhere in the app
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function levelVariant(level?: string) {
  if (!level) return "default";
  if (level === "critical") return "destructive";
  if (level === "high") return "warning";
  if (level === "medium") return "default";
  if (level === "low") return "success";
  return "default";
}

/**
 * Server component page
 */
export default async function RiskPage({
  params,
}: {
  params?: { orgId?: string };
}) {
  const orgId = (params?.orgId as string) ?? "400";

  // fetch the risk endpoint on server side so app/loading.tsx can show for suspending segments
  let data: any = null;
  try {
    const res = await fetch(`${API_BASE}/api/orgs/${encodeURIComponent(orgId)}/risk`, {
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch risk (${res.status})`);
    }
    data = await res.json();
  } catch (err) {
    // fallback minimal structure if fetch fails
    data = {
      status: "error",
      summary_stats: {
        high_risk_customers_count: 0,
        high_risk_exposure: 0,
        avg_dso_days: 0,
        total_overdue_receivables: 0,
      },
      customer_risk_scores: [],
      anomalies: [],
      early_warnings: [],
    };
  }

  // Normalize values with safe access
  const summary = data.summary_stats ?? {};
  const highRiskCount = Number(summary.high_risk_customers_count ?? 0);
  const highRiskExposure = Number(summary.high_risk_exposure ?? 0);
  const avgDso = Number(summary.avg_dso_days ?? summary.avg_dso_display ?? 0);
  const totalOverdue = Number(summary.total_overdue_receivables ?? 0);

  // Customers list - prefer customer_risk_scores, fall back to customers array
  const rawCustomers = Array.isArray(data.customer_risk_scores) && data.customer_risk_scores.length
    ? data.customer_risk_scores
    : Array.isArray(data.customers)
    ? data.customers
    : [];

  // Build quick lookup maps from different arrays (helps enrich missing fields)
  const customersById = new Map<string, any>();
  if (Array.isArray(data.customers)) {
    for (const c of data.customers) {
      const id = String(c.customer_id ?? c.customerId ?? c.id ?? "");
      customersById.set(id, c);
    }
  }

  const dsoByCustomerMap = new Map<string, any>();
  if (Array.isArray(data.dso_by_customer)) {
    for (const d of data.dso_by_customer) {
      const id = String(d.customer_id ?? d.customerId ?? d.id ?? "");
      dsoByCustomerMap.set(id, d);
    }
  }

  const customers: {
    customer_id?: string;
    customer_name?: string;
    risk_score?: number;
    total_outstanding_ar?: number;
    dso_days?: number;
    risk_level?: string;
  }[] = rawCustomers.map((c: any) => {
    const id = String(c.customer_id ?? c.customerId ?? c.id ?? c.customer_id ?? c.customer ?? "");

    // Try multiple locations for outstanding AR (in preferred order)
    let rawOutstanding: any =
      c.total_outstanding_ar ??
      c.total_outstanding ??
      c.remaining_amount ??
      c.total_outstanding_amount ??
      null;

    // Look in dso_by_customer (often has aggregated total_outstanding_ar)
    if (rawOutstanding == null) {
      const dsoEntry = dsoByCustomerMap.get(id);
      if (dsoEntry && (dsoEntry.total_outstanding_ar ?? dsoEntry.total_outstanding) != null) {
        rawOutstanding = dsoEntry.total_outstanding_ar ?? dsoEntry.total_outstanding;
      }
    }

    // Look in customers array as a fallback
    if (rawOutstanding == null) {
      const custEntry = customersById.get(id);
      if (custEntry && (custEntry.total_outstanding_ar ?? custEntry.total_outstanding) != null) {
        rawOutstanding = custEntry.total_outstanding_ar ?? custEntry.total_outstanding;
      }
    }

    // Coerce to number (handles numeric strings)
    const totalOutstandingNum = Number(rawOutstanding ?? 0);
    const resolvedOutstanding = Number.isFinite(totalOutstandingNum) ? totalOutstandingNum : 0;

    // dso_days can be present on multiple shapes
    const dso_days = Number(
      c.dso_days ??
        c.avg_dso_days ??
        (dsoByCustomerMap.get(id)?.avg_dso_days ?? dsoByCustomerMap.get(id)?.dso_days) ??
        customersById.get(id)?.dso_days ??
        0
    );

    const customer_name =
      (c.customer_name ?? c.customer ?? customersById.get(id)?.customer_name ?? "Unknown").toString();

    return {
      customer_id: id || undefined,
      customer_name,
      risk_score: Number(c.risk_score ?? c.riskScore ?? 0),
      total_outstanding_ar: resolvedOutstanding,
      dso_days,
      risk_level: (c.risk_level ?? c.riskLevel ?? c.level ?? "medium").toString(),
    };
  });

  const topCustomers = customers
    .slice()
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .slice(0, 6);

  // Anomalies / early warnings
  const anomalies: { type: string; description: string; detected?: string; severity?: string }[] =
    (data.anomalies && data.anomalies.length ? data.anomalies : []) ||
    (data.early_warnings && data.early_warnings.length
      ? data.early_warnings.map((w: string, i: number) => ({
          type: `Warning ${i + 1}`,
          description: String(w),
          detected: undefined,
          severity: "high",
        }))
      : []);

  // Derive distribution counts from customer_risk_scores
  const distribution = (data.customer_risk_scores ?? []).reduce(
    (acc: Record<string, number>, cur: any) => {
      const lvl = (cur.risk_level ?? cur.riskLevel ?? "unknown").toLowerCase();
      acc[lvl] = (acc[lvl] ?? 0) + 1;
      return acc;
    },
    {}
  );

  // Provide a default distribution if none present
  const distLow = distribution["low"] ?? 0;
  const distMedium = distribution["medium"] ?? 0;
  const distHigh = distribution["high"] ?? 0;
  const distCritical = distribution["critical"] ?? 0;

  // Compose top stat cards
  const stats = [
    {
      label: "HIGH RISK CUSTOMERS",
      value: String(highRiskCount),
      description: `${fmtCurrency(highRiskExposure)} EXPOSURE`,
      intent: highRiskCount > 0 ? ("destructive" as const) : ("default" as const),
      icon: AlertIcon,
      tag: highRiskCount > 0 ? "CRITICAL" : "OK",
    },
    {
      label: "AVG DSO",
      value: fmtNumber(avgDso),
      description: "DAYS SALES OUTSTANDING",
      intent: avgDso > 45 ? ("warning" as const) : ("default" as const),
      icon: AlertIcon,
      tag: "MONITOR",
    },
    {
      label: "OVERDUE RECEIVABLES",
      value: fmtCurrency(totalOverdue),
      description: "REQUIRES ATTENTION",
      intent: totalOverdue > 0 ? ("destructive" as const) : ("default" as const),
      icon: AlertIcon,
      tag: distHigh + distCritical > 0 ? "URGENT" : "OK",
    },
  ];

  return (
    <DashboardPageLayout
      header={{
        title: "Risk & Anomalies",
        description: "Financial risk detection",
        icon: AlertIcon,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {stats.map((stat, index) => (
          <DashboardStat
            key={index}
            label={stat.label}
            value={stat.value}
            description={stat.description}
            icon={stat.icon}
            tag={stat.tag}
            intent={stat.intent}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <DashboardCard title="CUSTOMER RISK SCORES" intent="destructive">
          <div className="space-y-3">
            {topCustomers.length === 0 && (
              <p className="text-sm text-muted-foreground">No customer risk scores available.</p>
            )}

            {topCustomers.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-accent rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1">
                  <Bullet variant={levelVariant(item.risk_level)} />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{item.customer_name}</p>
                    <p className="text-xs text-muted-foreground">DSO: {fmtNumber(item.dso_days)}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-display">
                    {fmtCurrency(item.total_outstanding_ar)}
                  </p>
                  <p className="text-xs text-muted-foreground">Risk: {fmtNumber(item.risk_score)}</p>
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>

        <DashboardCard title="DETECTED ANOMALIES" intent="destructive">
          <div className="space-y-3">
            {anomalies.length === 0 && (
              <p className="text-sm text-muted-foreground">No anomalies or early warnings detected.</p>
            )}
            {anomalies.map((item, index) => (
              <div
                key={index}
                className="flex items-start justify-between p-3 bg-accent rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="flex items-start gap-3 flex-1">
                  <Bullet
                    variant={item.severity === "critical" ? "destructive" : item.severity === "high" ? "warning" : "default"}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{item.type}</p>
                    <p className="text-xs text-muted-foreground mt-1">{item.description}</p>
                    {item.detected && <p className="text-xs text-muted-foreground mt-1">{item.detected}</p>}
                  </div>
                </div>
                <Badge
                  variant={
                    item.severity === "critical" ? "destructive" : item.severity === "high" ? "default" : "outline"
                  }
                  className="uppercase text-xs"
                >
                  {item.severity ?? "WARN"}
                </Badge>
              </div>
            ))}
          </div>
        </DashboardCard>
      </div>

      <DashboardCard title="RISK LEVEL DISTRIBUTION" intent="default">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-accent rounded-md text-center">
            <Bullet variant="success" className="mx-auto mb-2" />
            <p className="text-3xl font-display">{fmtNumber(distLow)}</p>
            <p className="text-xs text-muted-foreground uppercase mt-1">Low Risk</p>
          </div>
          <div className="p-4 bg-accent rounded-md text-center">
            <Bullet variant="default" className="mx-auto mb-2" />
            <p className="text-3xl font-display">{fmtNumber(distMedium)}</p>
            <p className="text-xs text-muted-foreground uppercase mt-1">Medium Risk</p>
          </div>
          <div className="p-4 bg-accent rounded-md text-center">
            <Bullet variant="warning" className="mx-auto mb-2" />
            <p className="text-3xl font-display">{fmtNumber(distHigh)}</p>
            <p className="text-xs text-muted-foreground uppercase mt-1">High Risk</p>
          </div>
          <div className="p-4 bg-accent rounded-md text-center">
            <Bullet variant="destructive" className="mx-auto mb-2" />
            <p className="text-3xl font-display">{fmtNumber(distCritical)}</p>
            <p className="text-xs text-muted-foreground uppercase mt-1">Critical</p>
          </div>
        </div>
      </DashboardCard>
    </DashboardPageLayout>
  );
}
