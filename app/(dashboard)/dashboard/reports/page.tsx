import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardCard from "@/components/dashboard/card"
import BracketsIcon from "@/components/icons/brackets"
import { Button } from "@/components/ui/button"
import { Bullet } from "@/components/ui/bullet"

const reports = [
  {
    title: "Weekly CFO Briefing",
    description: "Executive summary of financial health",
    lastGenerated: "3 hours ago",
    formats: ["PDF", "Email"],
  },
  {
    title: "Cashflow Report",
    description: "Detailed inflows and outflows analysis",
    lastGenerated: "1 day ago",
    formats: ["PDF", "Excel"],
  },
  {
    title: "Risk Assessment Report",
    description: "Customer risk scores and anomalies",
    lastGenerated: "2 days ago",
    formats: ["PDF", "CSV"],
  },
  {
    title: "Collections Report",
    description: "Receivables status and recovery metrics",
    lastGenerated: "1 day ago",
    formats: ["PDF", "Excel"],
  },
  {
    title: "Scenario Analysis Report",
    description: "What-if scenarios and sensitivity analysis",
    lastGenerated: "5 hours ago",
    formats: ["PDF"],
  },
]

export default function ReportsPage() {
  return (
    <DashboardPageLayout
      header={{
        title: "Reports & Exports",
        description: "Financial reporting",
        icon: BracketsIcon,
      }}
    >
      <DashboardCard title="AVAILABLE REPORTS" intent="default">
        <div className="space-y-3">
          {reports.map((report, index) => (
            <div key={index} className="p-4 bg-accent rounded-md hover:bg-accent/80 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start gap-3 flex-1">
                  <Bullet className="mt-1" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{report.title}</p>
                    <p className="text-xs text-muted-foreground mt-1">{report.description}</p>
                    <p className="text-xs text-muted-foreground mt-2">Last generated: {report.lastGenerated}</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-border">
                <div className="flex gap-2">
                  {report.formats.map((format) => (
                    <span key={format} className="text-xs text-muted-foreground">
                      {format}
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline">
                    Generate
                  </Button>
                  <Button size="sm">Download</Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </DashboardCard>
    </DashboardPageLayout>
  )
}
