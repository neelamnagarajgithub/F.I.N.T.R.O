import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardStat from "@/components/dashboard/stat"
import DashboardChart from "@/components/dashboard/chart"
import DashboardCard from "@/components/dashboard/card"
import TrendUpIcon from "@/components/icons/trend-up"
import TrendDownIcon from "@/components/icons/trend-down"
import { Badge } from "@/components/ui/badge"
import { Bullet } from "@/components/ui/bullet"

const DEFAULT_PERIOD_START = "2025-11-01"
const DEFAULT_PERIOD_END = "2025-12-19"
const DEFAULT_ORG_ID = 315

function formatAmount(value?: number | string) {
  const n = typeof value === "string" ? Number(value) : value ?? 0
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
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
  } catch {
    return iso
  }
}

function inferOutflowType(description = "") {
  const desc = description.toLowerCase()
  if (desc.includes("salary") || desc.includes("payroll") || desc.includes("rent") || desc.includes("loan") || desc.includes("emi")) {
    return "fixed"
  }
  return "variable"
}

// Strip common markdown patterns to plain text while preserving line breaks
function stripMarkdown(text?: string) {
  if (!text) return ""
  let s = String(text)

  // Remove code blocks and inline code
  s = s.replace(/```[\s\S]*?```/g, "")
  s = s.replace(/`([^`]*)`/g, "$1")

  // Remove headings (#, ##)
  s = s.replace(/^#{1,6}\s*/gm, "")

  // Convert bold/italic to plain text
  s = s.replace(/\*\*(.*?)\*\*/g, "$1")
  s = s.replace(/__(.*?)__/g, "$1")
  s = s.replace(/\*(.*?)\*/g, "$1")
  s = s.replace(/_(.*?)_/g, "$1")

  // Remove list markers
  s = s.replace(/^\s*[-*+]\s+/gm, "")

  // Remove ordered list numbers
  s = s.replace(/^\s*\d+\.\s+/gm, "")

  // Remove excessive multiple blank lines (keep at most two)
  s = s.replace(/\n{3,}/g, "\n\n")

  // Trim leading/trailing whitespace
  return s.trim()
}

export default async function CashflowPage() {
  const org_id = DEFAULT_ORG_ID
  const period_start = DEFAULT_PERIOD_START
  const period_end = DEFAULT_PERIOD_END

  // Prepare payloads
  const cashflowPayload = { org_id, period_start, period_end }

  let cashflowData: any = null
  let forecastData: any = null

  try {
    const [cfRes, fcRes] = await Promise.all([
      fetch("https://cfo-backend-883163069340.us-central1.run.app/cashflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cashflowPayload),
        cache: "no-store",
      }),
      // Use GET with query param for forecast as requested
      fetch(`https://cfo-backend-883163069340.us-central1.run.app/forecast?org_id=${encodeURIComponent(org_id)}`, {
        method: "GET",
        cache: "no-store",
      }),
    ])

    if (!cfRes.ok) throw new Error(`Cashflow fetch failed: ${cfRes.status}`)
    if (!fcRes.ok) throw new Error(`Forecast fetch failed: ${fcRes.status}`)

    cashflowData = await cfRes.json()
    forecastData = await fcRes.json()
  } catch (err) {
    console.error("Error fetching cashflow/forecast:", err)
    // Safe fallbacks so UI won't crash
    cashflowData = cashflowData ?? {
      payments: [],
      inflows: 0,
      outflows: 0,
      net_cashflow: 0,
      opening_balance: 0,
      closing_balance: 0,
      burn_rate: 0,
      risk_level: "UNKNOWN",
      explanation:
        "Unable to fetch cashflow from local server. Please ensure https://cfo-backend-883163069340.us-central1.run.app/cashflow is running.",
    }
    forecastData = forecastData ?? {
      status: "error",
      forecast: [],
      drivers: { top_inflows: [], top_outflows: [] },
      model_info: null,
      summary: null,
    }
  }

  // Build UI values from cashflow response
  const cashflowStats = [
    {
      label: "TOTAL INFLOWS",
      value: formatAmount(cashflowData.inflows),
      description: `${period_start} → ${period_end}`,
      intent: "positive" as const,
      icon: TrendUpIcon,
      direction: "up" as const,
    },
    {
      label: "TOTAL OUTFLOWS",
      value: formatAmount(cashflowData.outflows),
      description: `${period_start} → ${period_end}`,
      intent: "neutral" as const,
      icon: TrendDownIcon,
      direction: "down" as const,
    },
    {
      label: "NET CASHFLOW",
      value: formatAmount(cashflowData.net_cashflow),
      description: "Period net",
      intent: (cashflowData.net_cashflow ?? 0) >= 0 ? ("positive" as const) : ("negative" as const),
      icon: (cashflowData.net_cashflow ?? 0) >= 0 ? TrendUpIcon : TrendDownIcon,
      direction: (cashflowData.net_cashflow ?? 0) >= 0 ? ("up" as const) : ("down" as const),
    },
  ]

  const payments: Array<any> = Array.isArray(cashflowData.payments) ? cashflowData.payments : []

  const inflowDrivers = payments
    .filter((p) => p.payment_type === "inflow")
    .slice(0, 6)
    .map((p) => ({
      customer: p.description ?? "Inflow",
      amount: formatAmount(Number(p.payment_amount)),
      date: formatDateShort(p.payment_date),
      status: p.status ?? "unknown",
    }))

  const outflowDrivers = payments
    .filter((p) => p.payment_type === "outflow")
    .slice(0, 6)
    .map((p) => ({
      vendor: p.description ?? "Outflow",
      amount: formatAmount(Number(p.payment_amount)),
      date: formatDateShort(p.payment_date),
      type: inferOutflowType(p.description),
    }))

  const forecastList: Array<any> = Array.isArray(forecastData.forecast) ? forecastData.forecast : []
  const forecastSummary: any = forecastData.summary ?? null
  const modelInfo: any = forecastData.model_info ?? null

  return (
    <DashboardPageLayout
      header={{
        title: "Cashflow & Forecast",
        description: "13-week cash projection",
        icon: TrendUpIcon,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {cashflowStats.map((stat, index) => (
          <DashboardStat
            key={index}
            label={stat.label}
            value={stat.value}
            description={stat.description}
            icon={stat.icon}
            intent={stat.intent}
            direction={stat.direction}
          />
        ))}
      </div>

      <div className="mb-6">
        <DashboardChart />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <DashboardCard title="FORECAST SUMMARY" intent="default">
            <div className="p-3 bg-accent rounded-md space-y-2">
              <p className="text-sm text-muted-foreground">Forecast Window</p>
              <p className="text-lg font-display">
                {forecastSummary ? `${forecastSummary.forecast_start} → ${forecastSummary.forecast_end}` : "—"}
              </p>

              <div className="pt-2 border-t border-border/50">
                <p className="text-xs text-muted-foreground uppercase">Current Balance</p>
                <p className="text-2xl font-display">{forecastSummary ? formatAmount(forecastSummary.current_balance) : "—"}</p>

                <p className="text-xs text-muted-foreground uppercase mt-2">Ending Balance</p>
                <p className="text-2xl font-display">{forecastSummary ? formatAmount(forecastSummary.ending_balance) : "—"}</p>
              </div>
            </div>
          </DashboardCard>

          <DashboardCard title="FORECAST MODEL INFO" intent="default">
            <div className="p-3 bg-accent rounded-md space-y-2 text-sm">
              <p><strong>Model:</strong> {modelInfo?.model_type ?? "—"} {modelInfo?.model_version ?? ""}</p>
              <p><strong>MAPE:</strong> {modelInfo?.mape ? `${Number(modelInfo.mape).toFixed(2)}%` : "—"}</p>
              <p><strong>Training Date:</strong> {modelInfo?.training_date ? new Date(modelInfo.training_date).toLocaleString() : "—"}</p>
            </div>
          </DashboardCard>
        </div>

        <DashboardCard title="AGENT VIEW: EXPLANATION" intent="default" className="mt-4">
          <div className="p-3 bg-accent rounded-md">
            <pre className="whitespace-pre-wrap text-sm m-0">{stripMarkdown(cashflowData.explanation)}</pre>
          </div>
        </DashboardCard>

        <DashboardCard title="UPCOMING FORECAST (NEXT 7 DAYS)" intent="default" className="mt-4">
          <div className="space-y-2 p-3 bg-accent rounded-md">
            {forecastList.length === 0 && <p className="text-sm text-muted-foreground">No forecast data available.</p>}
            {forecastList.slice(0, 7).map((f: any, i: number) => (
              <div key={i} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{f.date}</p>
                  <p className="text-xs text-muted-foreground">{formatAmount(f.predicted_balance)}</p>
                </div>
                <div className="text-right">
                  <p className={`text-sm ${f.daily_change >= 0 ? "text-success" : "text-destructive"}`}>
                    {f.daily_change >= 0 ? "+" : ""}
                    {formatAmount(f.daily_change)}
                  </p>
                  <p className="text-xs text-muted-foreground">95% CI: {formatAmount(f.confidence_5)} — {formatAmount(f.confidence_95)}</p>
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DashboardCard title="TOP INFLOW DRIVERS" intent="success">
          <div className="space-y-3">
            {inflowDrivers.length === 0 && <p className="text-sm text-muted-foreground">No inflows in the selected period.</p>}
            {inflowDrivers.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-accent rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1">
                  <Bullet variant={item.status === "completed" ? "success" : "default"} />
                  <div>
                    <p className="text-sm font-medium">{item.customer}</p>
                    <p className="text-xs text-muted-foreground">{item.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-display">{item.amount}</p>
                  <Badge variant={item.status === "completed" ? "default" : "outline"} className="text-xs">
                    {item.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>

        <DashboardCard title="TOP OUTFLOW DRIVERS" intent="default">
          <div className="space-y-3">
            {outflowDrivers.length === 0 && <p className="text-sm text-muted-foreground">No outflows in the selected period.</p>}
            {outflowDrivers.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-accent rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1">
                  <Bullet variant={item.type === "fixed" ? "warning" : "default"} />
                  <div>
                    <p className="text-sm font-medium">{item.vendor}</p>
                    <p className="text-xs text-muted-foreground">{item.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-display">{item.amount}</p>
                  <Badge variant={item.type === "fixed" ? "default" : "outline"} className="text-xs">
                    {item.type}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>
      </div>
    </DashboardPageLayout>
  )
}
