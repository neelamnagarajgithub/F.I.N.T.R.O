import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardStat from "@/components/dashboard/stat"
import DashboardChart from "@/components/dashboard/chart"
import DashboardCard from "@/components/dashboard/card"
import BracketsIcon from "@/components/icons/brackets"
import TrendUpIcon from "@/components/icons/trend-up"
import AlertIcon from "@/components/icons/alert"
import DollarIcon from "@/components/icons/dollar"
import mockDataJson from "@/mock.json"
import type { MockData } from "@/types/dashboard"
import { Badge } from "@/components/ui/badge"
import { Bullet } from "@/components/ui/bullet"

const mockData = mockDataJson as MockData

const cfoStats = [
  {
    label: "CURRENT CASH BALANCE",
    value: "$842K",
    description: "AS OF TODAY",
    intent: "positive" as const,
    icon: DollarIcon,
    direction: "up" as const,
  },
  {
    label: "NET CASHFLOW",
    value: "$124K",
    description: "MONTH TO DATE",
    intent: "positive" as const,
    icon: TrendUpIcon,
    direction: "up" as const,
  },
  {
    label: "RUNWAY DAYS",
    value: "147",
    description: "BASED ON CURRENT BURN RATE",
    intent: "neutral" as const,
    icon: AlertIcon,
    tag: "HEALTHY",
  },
]

const insights = {
  risks: [
    {
      title: "Large payroll due in 5 days",
      amount: "$180K",
      severity: "high" as const,
    },
    {
      title: "Customer payment delays trending up",
      amount: "+12% DSO",
      severity: "medium" as const,
    },
    {
      title: "Q4 tax payment approaching",
      amount: "$95K",
      severity: "medium" as const,
    },
  ],
  opportunities: [
    {
      title: "Early payment discount available",
      amount: "Save $8.5K",
      severity: "positive" as const,
    },
    {
      title: "Collections can be accelerated",
      amount: "$120K recoverable",
      severity: "positive" as const,
    },
    {
      title: "Vendor payment deferral option",
      amount: "$45K flexibility",
      severity: "positive" as const,
    },
  ],
}

const activitySnapshot = [
  {
    label: "COLLECTIONS DUE TODAY",
    value: "8",
    amount: "$67.5K",
    status: "pending",
  },
  {
    label: "HIGH-RISK CUSTOMERS",
    value: "3",
    amount: "$142K outstanding",
    status: "warning",
  },
  {
    label: "CRITICAL ALERTS",
    value: "2",
    amount: "Requires action",
    status: "critical",
  },
]

export default function DashboardOverview() {
  return (
    <DashboardPageLayout
      header={{
        title: "Executive Overview",
        description: "Last updated 12:05",
        icon: BracketsIcon,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
        {cfoStats.map((stat, index) => (
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
        {/* Top 3 Risks */}
        <DashboardCard title="TOP 3 RISKS THIS WEEK" intent="default">
          <div className="space-y-4">
            {insights.risks.map((risk, index) => (
              <div
                key={index}
                className="flex items-start justify-between p-3 bg-accent rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="flex items-start gap-3 flex-1">
                  <Bullet
                    variant={
                      risk.severity === "high" ? "destructive" : risk.severity === "medium" ? "warning" : "default"
                    }
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{risk.title}</p>
                    <p className="text-xs text-muted-foreground mt-1">{risk.amount}</p>
                  </div>
                </div>
                <Badge
                  variant={
                    risk.severity === "high" ? "destructive" : risk.severity === "medium" ? "default" : "outline"
                  }
                  className="uppercase text-xs"
                >
                  {risk.severity}
                </Badge>
              </div>
            ))}
          </div>
        </DashboardCard>

        {/* Top 3 Opportunities */}
        <DashboardCard title="TOP 3 OPPORTUNITIES THIS WEEK" intent="success">
          <div className="space-y-4">
            {insights.opportunities.map((opportunity, index) => (
              <div
                key={index}
                className="flex items-start justify-between p-3 bg-accent rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="flex items-start gap-3 flex-1">
                  <Bullet variant="success" className="mt-1" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{opportunity.title}</p>
                    <p className="text-xs text-success mt-1">{opportunity.amount}</p>
                  </div>
                </div>
                <Badge variant="outline" className="uppercase text-xs">
                  OPPORTUNITY
                </Badge>
              </div>
            ))}
          </div>
        </DashboardCard>
      </div>

      <DashboardCard title="ACTIVITY SNAPSHOT" intent="default">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {activitySnapshot.map((activity, index) => (
            <div key={index} className="p-4 bg-accent rounded-md hover:bg-accent/80 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Bullet
                  variant={
                    activity.status === "critical"
                      ? "destructive"
                      : activity.status === "warning"
                        ? "warning"
                        : "default"
                  }
                />
                <p className="text-xs font-medium text-muted-foreground tracking-wide uppercase">{activity.label}</p>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl md:text-4xl font-display">{activity.value}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">{activity.amount}</p>
            </div>
          ))}
        </div>
      </DashboardCard>
    </DashboardPageLayout>
  )
}
