import DashboardPageLayout from "@/components/dashboard/layout";
import DashboardCard from "@/components/dashboard/card";
import DashboardStat from "@/components/dashboard/stat";
import DollarIcon from "@/components/icons/dollar";
import { Badge } from "@/components/ui/badge";
import { Bullet } from "@/components/ui/bullet";
import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "https://cfo-backend-883163069340.us-central1.run.app";
const APP_BASE = process.env.NEXT_PUBLIC_APP_BASE ?? "https://fintro-backend-883163069340.asia-south1.run.app";

function fmtCurrency(value: number | string | undefined) {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtNumber(value: number | string | undefined) {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-IN");
}

export default async function CollectionsPage({
  params,
}: {
  params?: { orgId?: string };
}) {
  const orgId = (params?.orgId as string) ?? "315";

  let data: any = null;
  try {
    const res = await fetch(`${API_BASE}/api/orgs/${encodeURIComponent(orgId)}/collections`, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        base_url: APP_BASE,
        top_k_calls_today: 10,
      }),
    });

    if (!res.ok) {
      throw new Error(`Collections request failed (${res.status})`);
    }
    data = await res.json();
  } catch (err) {
    data = {
      prioritized_today: [],
      full_queue: [],
      drafted_reminders: {},
      recovery_metrics: {},
    };
  }

  const prioritized: any[] = Array.isArray(data.prioritized_today) ? data.prioritized_today : [];
  const fullQueue: any[] = Array.isArray(data.full_queue) ? data.full_queue : [];
  const draftedReminders: Record<string, string> = data.drafted_reminders ?? {};
  const recoveryMetrics: any = data.recovery_metrics ?? {};

  const totalOutstanding =
    recoveryMetrics.total_amount_contacted ??
    prioritized.reduce((s: number, it: any) => s + Number(it.amount ?? 0), 0);

  const collectionStats = [
    {
      label: "TOTAL OUTSTANDING",
      value: fmtCurrency(totalOutstanding),
      description: `${fmtNumber(prioritized.length || fullQueue.length)} ITEMS`,
      intent: "neutral" as const,
      icon: DollarIcon,
    },
    {
      label: "PRIORITIZED TODAY",
      value: String(prioritized.length),
      description: "HIGH PRIORITY INVOICES",
      intent: (prioritized.length > 0 ? "warning" : "default") as const,
      icon: DollarIcon,
      tag: prioritized.length > 0 ? "ACTION" : undefined,
    },
    {
      label: "RECOVERY POTENTIAL",
      value:
        recoveryMetrics.potential_recovery_amount != null
          ? fmtCurrency(recoveryMetrics.potential_recovery_amount)
          : "—",
      description: `${recoveryMetrics.period_days ?? "30"} DAYS`,
      intent: "positive" as const,
      icon: DollarIcon,
    },
  ];

  return (
    <DashboardPageLayout
      header={{
        title: "Collections & Interventions",
        description: "Receivables management",
        icon: DollarIcon,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {collectionStats.map((stat, index) => (
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

      <DashboardCard title="PRIORITIZED COLLECTIONS QUEUE" intent="default" className="mb-6">
        <div className="space-y-3">
          {prioritized.length === 0 && (
            <p className="text-sm text-muted-foreground">No prioritized collections for today.</p>
          )}

          {prioritized.map((item, index) => (
            <div key={index} className="p-4 bg-accent rounded-md hover:bg-accent/80 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start gap-3 flex-1">
                  <Bullet
                    variant={
                      item.priority_score > 300
                        ? "destructive"
                        : item.priority_score > 150
                        ? "warning"
                        : "default"
                    }
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{item.customer_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.days_overdue} days overdue • Priority: {fmtNumber(item.priority_score)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-display">{fmtCurrency(item.amount)}</p>
                  <Badge variant="outline" className="text-xs mt-1">
                    {item.recommended_channel ?? "email"}
                  </Badge>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-border">
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground uppercase mb-1">Suggested Intervention</p>
                  <p className="text-sm capitalize">{item.recommended_intervention ?? "escalate_to_collections"}</p>
                    </div>

                <div className="flex gap-2">
                  {item.draft_message ? (
                    // mailto link with draft body encoded
                    <a
                      href={`mailto:?subject=${encodeURIComponent(
                        `Reminder: Invoice ${item.invoice_id} — ${item.customer_name}`
                      )}&body=${encodeURIComponent(item.draft_message)}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Button size="sm">Open Draft</Button>
                    </a>
                  ) : (
                    <Button size="sm" variant="outline" disabled>
                      No Draft
                    </Button>
                  )}

                  <Button size="sm" variant="ghost">
                    Details
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </DashboardCard>

      <DashboardCard title="COLLECTION METRICS" intent="success">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-accent rounded-md text-center">
            <p className="text-xs text-muted-foreground uppercase mb-2">Collection Effectiveness</p>
            <p className="text-3xl font-display mb-1">
              {data.channel_effectiveness
                ? `${Math.round((data.channel_effectiveness?.whatsapp?.collection_pct ?? 0) * 100)}%`
                : "—"}
            </p>
            <p className="text-xs text-success">Best channel: WhatsApp</p>
          </div>

          <div className="p-4 bg-accent rounded-md text-center">
            <p className="text-xs text-muted-foreground uppercase mb-2">DSO (Current)</p>
            <p className="text-3xl font-display mb-1">
              {data.dso_improvement_potential?.current_dso ?? "—"}
            </p>
            <p className="text-xs text-success">Est. after actions: {data.dso_improvement_potential?.estimated_dso ?? "—"}</p>
          </div>

          <div className="p-4 bg-accent rounded-md text-center">
            <p className="text-xs text-muted-foreground uppercase mb-2">Recovery Metrics</p>
            <p className="text-3xl font-display mb-1">
              {recoveryMetrics.potential_recovery_amount != null
                ? fmtCurrency(recoveryMetrics.potential_recovery_amount)
                : "—"}
            </p>
            <p className="text-xs text-success">Contacted: {fmtCurrency(recoveryMetrics.total_amount_contacted)}</p>
          </div>
        </div>
      </DashboardCard>
    </DashboardPageLayout>
  );
}