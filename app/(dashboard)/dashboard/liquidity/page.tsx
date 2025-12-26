import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardCard from "@/components/dashboard/card"
import DashboardStat from "@/components/dashboard/stat"
import DashboardChart from "@/components/dashboard/chart"
import DollarIcon from "@/components/icons/dollar"
import AlertIcon from "@/components/icons/alert"
import { Badge } from "@/components/ui/badge"
import { Bullet } from "@/components/ui/bullet"
import { Button } from "@/components/ui/button"

const DEFAULT_ORG_ID = 315

function formatAmount(value?: number | string) {
  const n = typeof value === "string" ? Number(value) : value ?? 0
  // show absolute amounts with currency sign; negative numbers will show with minus
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n)
}

function formatDateShort(iso?: string) {
  if (!iso) return ""
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
  } catch {
    return iso
  }
}

export default async function LiquidityPage() {
  const org_id = DEFAULT_ORG_ID

  let collisionsResp: any = null

  try {
    const res = await fetch(`https://cfo-backend-883163069340.us-central1.run.app/api/orgs/${encodeURIComponent(org_id)}/collisions`, {
      method: "GET",
      cache: "no-store",
    })

    if (!res.ok) throw new Error(`Collisions fetch failed: ${res.status}`)
    collisionsResp = await res.json()
  } catch (err) {
    console.error("Error fetching collisions:", err)
    collisionsResp = {
      status: "error",
      current_position: {
        current_balance: 0,
        minimum_balance: 0,
        balance_gap: 0,
        available_credit: 0,
        credit_utilization_pct: 0,
      },
      collision_analysis: {
        total_collisions_detected: 0,
        critical_collisions: 0,
        high_collisions: 0,
        first_collision: null,
        collisions_91d: [],
      },
      emergency_action_plan: { action_date: null, priority_actions: [] },
      recommendation: { immediate_action: "NONE", message: "" },
    }
  }

  const current = collisionsResp.current_position ?? {}
  const analysis = collisionsResp.collision_analysis ?? {}
  const firstCollision = analysis.first_collision ?? null
  const collisionsList = Array.isArray(analysis.collisions_91d) ? analysis.collisions_91d : []
  const emergencyPlan = collisionsResp.emergency_action_plan ?? { priority_actions: [] }
  const recommendation = collisionsResp.recommendation ?? {}

  const liquidityStats = [
    {
      label: "CURRENT BALANCE",
      value: formatAmount(current.current_balance),
      description: "AVAILABLE NOW",
      intent: (current.current_balance ?? 0) >= 0 ? ("positive" as const) : ("destructive" as const),
      icon: DollarIcon,
      direction: (current.current_balance ?? 0) >= 0 ? ("up" as const) : ("down" as const),
    },
    {
      label: "MIN BALANCE (90D)",
      value: formatAmount(current.minimum_balance ?? 0),
      description: "FORECASTED MINIMUM",
      intent: "warning" as const,
      icon: AlertIcon,
      tag: "WATCH",
    },
    {
      label: "COLLISION EVENTS",
      value: String(analysis.total_collisions_detected ?? 0),
      description: "NEXT 91 DAYS",
      intent: (analysis.critical_collisions ?? 0) > 0 ? ("destructive" as const) : ("neutral" as const),
      icon: AlertIcon,
      tag: (analysis.critical_collisions ?? 0) > 0 ? "URGENT" : undefined,
    },
  ]

  return (
    <DashboardPageLayout
      header={{
        title: "Liquidity & Collisions",
        description: "Cash crunch detection",
        icon: DollarIcon,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {liquidityStats.map((stat, index) => (
          <DashboardStat
            key={index}
            label={stat.label}
            value={stat.value}
            description={stat.description}
            icon={stat.icon}
            tag={stat.tag}
            intent={stat.intent}
            direction={stat.direction}
          />
        ))}
      </div>

      <div className="mb-6">
        <DashboardChart />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <DashboardCard title="NEXT COLLISIONS (TOP 6)" intent="destructive">
          <div className="space-y-4">
            {collisionsList.length === 0 && <p className="text-sm text-muted-foreground">No collisions detected.</p>}
            {collisionsList.slice(0, 6).map((c: any, idx: number) => (
              <div key={idx} className="p-4 bg-accent rounded-md hover:bg-accent/80 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Bullet variant={c.severity === "critical" ? "destructive" : c.severity === "high" ? "warning" : "default"} />
                    <div>
                      <p className="text-sm font-medium">{formatDateShort(c.collision_date ?? c.collision_date)}</p>
                      <p className="text-xs text-muted-foreground">{c.days_from_now != null ? `${c.days_from_now} days from now` : ""}</p>
                    </div>
                  </div>
                  <Badge variant={c.severity === "critical" ? "destructive" : "default"} className="uppercase text-xs">
                    {c.severity ?? "unknown"}
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Predicted Balance</p>
                    <p className="text-2xl font-display">{formatAmount(c.predicted_balance ?? 0)}</p>
                    <p className="text-xs text-muted-foreground mt-1">Deficit: {formatAmount(c.deficit_amount ?? 0)}</p>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Mitigation</p>
                    {Array.isArray(c.mitigation_levers) && c.mitigation_levers.length > 0 ? (
                      <ul className="text-sm list-inside list-disc">
                        {c.mitigation_levers.slice(0, 3).map((m: any, i: number) => (
                          <li key={i}>
                            {m.lever} — {formatAmount(m.potential_amount ?? 0)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm">No mitigation suggestions</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>

        <DashboardCard title="EMERGENCY ACTION PLAN" intent="warning">
          <div className="space-y-3 p-4 bg-accent rounded-md">
            <p className="text-xs text-muted-foreground">Plan date: {emergencyPlan.action_date ?? "—"}</p>

            {Array.isArray(emergencyPlan.priority_actions) && emergencyPlan.priority_actions.length > 0 ? (
              <div className="space-y-2">
                {emergencyPlan.priority_actions.map((a: any, i: number) => (
                  <div key={i} className="p-3 bg-muted rounded">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium">{a.action}</p>
                        <p className="text-xs text-muted-foreground mt-1">Owner: {a.owner ?? "—"} — Deadline: {a.deadline ?? "—"}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-display">{a.amount ? formatAmount(a.amount) : a.expected_recovery ? formatAmount(a.expected_recovery) : "—"}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No emergency actions available.</p>
            )}

            <div className="pt-3 flex gap-2">
              <Button variant="destructive" size="sm">Run Simulation</Button>
              <Button size="sm" variant="outline">Contact Top Customers</Button>
            </div>
          </div>
        </DashboardCard>
      </div>
    </DashboardPageLayout>
  )
}
