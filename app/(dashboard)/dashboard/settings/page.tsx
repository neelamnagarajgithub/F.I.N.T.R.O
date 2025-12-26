import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardCard from "@/components/dashboard/card"
import GearIcon from "@/components/icons/gear"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Bullet } from "@/components/ui/bullet"

const integrations = [
  { name: "Bank Connection", status: "connected", provider: "HDFC Bank" },
  { name: "Accounting Software", status: "connected", provider: "Zoho Books" },
  { name: "CRM Integration", status: "not-connected", provider: "Salesforce" },
  { name: "WhatsApp Business", status: "connected", provider: "Meta" },
  { name: "Email Provider", status: "connected", provider: "SendGrid" },
]

export default function SettingsPage() {
  return (
    <DashboardPageLayout
      header={{
        title: "Settings & Integrations",
        description: "Configure dashboard",
        icon: GearIcon,
      }}
    >
      <DashboardCard title="INTEGRATIONS" intent="default" className="mb-6">
        <div className="space-y-3">
          {integrations.map((integration, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-accent rounded-md">
              <div className="flex items-center gap-3 flex-1">
                <Bullet variant={integration.status === "connected" ? "success" : "default"} />
                <div>
                  <p className="text-sm font-medium">{integration.name}</p>
                  <p className="text-xs text-muted-foreground">{integration.provider}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={integration.status === "connected" ? "default" : "outline"} className="text-xs">
                  {integration.status}
                </Badge>
                <Button size="sm" variant="outline">
                  {integration.status === "connected" ? "Configure" : "Connect"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </DashboardCard>

      <DashboardCard title="ALERT THRESHOLDS" intent="default" className="mb-6">
        <div className="space-y-4">
          <div>
            <Label htmlFor="min-balance" className="text-xs uppercase text-muted-foreground">
              Minimum Balance Alert ($)
            </Label>
            <Input id="min-balance" type="number" placeholder="100000" className="mt-2" />
          </div>
          <div>
            <Label htmlFor="runway" className="text-xs uppercase text-muted-foreground">
              Runway Alert (days)
            </Label>
            <Input id="runway" type="number" placeholder="90" className="mt-2" />
          </div>
          <div>
            <Label htmlFor="dso" className="text-xs uppercase text-muted-foreground">
              DSO Alert (days)
            </Label>
            <Input id="dso" type="number" placeholder="45" className="mt-2" />
          </div>
          <Button>Save Settings</Button>
        </div>
      </DashboardCard>

      <DashboardCard title="USER ROLES & PERMISSIONS" intent="default">
        <div className="space-y-3">
          {["CFO", "Finance Manager", "Accountant"].map((role, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-accent rounded-md">
              <div className="flex items-center gap-3">
                <Bullet />
                <p className="text-sm font-medium">{role}</p>
              </div>
              <Button size="sm" variant="outline">
                Manage
              </Button>
            </div>
          ))}
        </div>
      </DashboardCard>
    </DashboardPageLayout>
  )
}
