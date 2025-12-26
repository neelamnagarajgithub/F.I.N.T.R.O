import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, TrendingUp, AlertTriangle, DollarSign, BarChart3, Target, MessageSquare } from "lucide-react"

export default function LandingPage() {
  const problems = [
    "Cash is spread across tools (banks, invoices, payroll, vendors)",
    "No real-time visibility into runway",
    "Forecasts live in Excel and go stale instantly",
    "Risks are discovered too late",
    "Founders react instead of plan",
    "Hiring a CFO is expensive and delayed",
  ]

  const capabilities = [
    {
      icon: DollarSign,
      title: "Cash Intelligence",
      points: ["Real-time inflows and outflows", "Burn tracking and category drivers"],
    },
    {
      icon: TrendingUp,
      title: "Runway & Forecasting",
      points: ["Predict runway days and cash crunches", "30 / 60 / 90 day forecasts"],
    },
    {
      icon: AlertTriangle,
      title: "Risk Detection",
      points: ["Expense spikes", "Revenue drops", "Vendor and customer risk"],
    },
    {
      icon: BarChart3,
      title: "Collections & Recovery",
      points: ["Prioritized receivables", "Suggested interventions", "Expected recovery impact"],
    },
    {
      icon: Target,
      title: "Scenario Simulation",
      points: ["What-if modeling for decisions", "Compare base vs modified outcomes"],
    },
    {
      icon: MessageSquare,
      title: "CFO Copilot",
      points: ["Ask financial questions in natural language", "Get reasoned answers with confidence levels"],
    },
  ]

  const useCases = [
    "How long can we survive if revenue drops 20%?",
    "What happens if collections slip by 15 days?",
    "Can we afford this hire next month?",
    "Which customer should we chase today?",
  ]

  const differentiators = [
    { label: "Autonomous vs Manual", description: "Continuous monitoring, not periodic checks" },
    { label: "Proactive vs Reactive", description: "Predict problems before they happen" },
    { label: "Reasoning vs Reporting", description: "Why and what to do, not just what happened" },
    { label: "Action-oriented vs Insight-only", description: "Decisions, not just dashboards" },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl font-display text-primary">FINTRO</div>
              <Badge variant="outline" className="uppercase text-xs border-primary/50">
                AI CFO
              </Badge>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/login">
                <Button variant="ghost" size="sm" className="font-mono">
                  Log in
                </Button>
              </Link>
              <Link href="/signup">
                <Button size="sm" className="bg-primary hover:bg-primary/90 font-mono">
                  Request Early Access
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 lg:px-8 pt-16 pb-20 lg:pt-24 lg:pb-32">
        <div className="max-w-5xl mx-auto text-center">
          <Badge variant="outline" className="mb-6 uppercase text-xs border-success/50">
            <span className="w-2 h-2 bg-success rounded-full inline-block mr-2 animate-pulse" />
            Early Access Available
          </Badge>
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-display text-foreground mb-6 leading-tight text-balance">
            An Autonomous AI CFO That Monitors Cash & Predicts Runway
          </h1>
          <p className="text-base md:text-lg font-mono text-muted-foreground mb-4 max-w-3xl mx-auto">
            Proactive, agent-driven, forward-looking financial intelligence.
          </p>
          <p className="text-base md:text-lg font-mono text-muted-foreground mb-10 max-w-3xl mx-auto">
            Fintro tells founders what to do before money runs out.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link href="/signup">
              <Button size="lg" className="bg-primary hover:bg-primary/90 h-12 px-8 font-mono">
                Request Early Access
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="#how-it-works">
              <Button size="lg" variant="outline" className="h-12 px-8 bg-transparent font-mono">
                See How It Works
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="container mx-auto px-4 lg:px-8 py-20 bg-accent/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-4">
              Why Founders Lose Control of Cash
            </h2>
            <p className="text-base font-mono text-muted-foreground max-w-2xl mx-auto">
              Real problems that kill startups every day
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4 max-w-4xl mx-auto">
            {problems.map((problem, index) => (
              <div
                key={index}
                className="bg-background border border-border rounded-lg p-6 hover:border-error/50 transition-all flex items-start gap-3"
              >
                <div className="w-2 h-2 bg-error rounded-full mt-2 flex-shrink-0" />
                <p className="text-sm font-mono text-foreground">{problem}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="container mx-auto px-4 lg:px-8 py-20">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-6">What Fintro Does Differently</h2>
            <p className="text-base font-mono text-muted-foreground max-w-3xl mx-auto mb-8">
              Fintro is not a dashboard. Not accounting software. Not static reports.
            </p>
            <div className="inline-block bg-accent border border-primary/30 rounded-lg p-6 text-left max-w-2xl">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                  <p className="text-sm font-mono text-foreground">
                    Autonomous AI agents continuously monitor finances
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                  <p className="text-sm font-mono text-foreground">
                    Cashflow, runway, risk, and collections are reasoned — not reported
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                  <p className="text-sm font-mono text-foreground">Decisions are forward-looking, not historical</p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                  <p className="text-sm font-mono text-foreground">The system behaves like a CFO, not software</p>
                </div>
              </div>
            </div>
          </div>

          <div className="text-center mt-12">
            <p className="text-2xl font-display text-success mb-2">✓ An Autonomous Financial Decision Engine</p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="container mx-auto px-4 lg:px-8 py-20 bg-accent/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-4">How Fintro Works</h2>
            <p className="text-base font-mono text-muted-foreground">Agent-based autonomous financial intelligence</p>
          </div>

          <div className="space-y-4 max-w-3xl mx-auto">
            {[
              "Connect financial data sources",
              "Agents ingest and normalize data",
              "Cashflow and burn are continuously calculated",
              "Runway and risk are predicted in advance",
              "Scenarios are simulated",
              "Actions and recommendations are generated",
            ].map((step, index) => (
              <div key={index} className="bg-background border border-border rounded-lg p-6 flex items-center gap-4">
                <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-xl font-display text-primary">{index + 1}</span>
                </div>
                <p className="text-sm font-mono text-foreground">{step}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Core Capabilities */}
      <section className="container mx-auto px-4 lg:px-8 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-4">Core Capabilities</h2>
            <p className="text-base font-mono text-muted-foreground">Everything a CFO does, automated</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {capabilities.map((capability, index) => (
              <div
                key={index}
                className="bg-accent border border-border rounded-lg p-6 hover:border-primary/50 transition-all"
              >
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <capability.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-lg font-display text-foreground mb-3">{capability.title}</h3>
                <div className="space-y-2">
                  {capability.points.map((point, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-primary rounded-full mt-1.5 flex-shrink-0" />
                      <p className="text-xs font-mono text-muted-foreground">{point}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Who It's For */}
      <section className="container mx-auto px-4 lg:px-8 py-20 bg-accent/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-4">Who Fintro Is For</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {[
              { title: "Startup Founders", subtitle: "Seed to Series B" },
              { title: "SMB Owners", subtitle: "Growth Stage" },
              { title: "Finance Leaders", subtitle: "Without Full CFO Team" },
            ].map((segment, index) => (
              <div key={index} className="bg-background border border-success/50 rounded-lg p-6 text-center">
                <h3 className="text-lg font-display text-foreground mb-1">{segment.title}</h3>
                <p className="text-sm font-mono text-muted-foreground">{segment.subtitle}</p>
              </div>
            ))}
          </div>

          <div className="text-center mt-8 p-6 bg-background border border-border rounded-lg max-w-2xl mx-auto">
            <p className="text-sm font-display text-muted-foreground mb-2">NOT FOR:</p>
            <p className="text-xs font-mono text-muted-foreground">
              Enterprises with large finance teams • Simple bookkeeping needs
            </p>
          </div>
        </div>
      </section>

      {/* Why Fintro Wins */}
      <section className="container mx-auto px-4 lg:px-8 py-20">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-4">Why Fintro Wins</h2>
            <p className="text-base font-mono text-muted-foreground">
              vs Accounting Software • BI Dashboards • Excel Models
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4 max-w-3xl mx-auto">
            {differentiators.map((diff, index) => (
              <div key={index} className="bg-accent border border-border rounded-lg p-6">
                <h3 className="text-base font-display text-primary mb-2">{diff.label}</h3>
                <p className="text-sm font-mono text-muted-foreground">{diff.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="container mx-auto px-4 lg:px-8 py-20 bg-accent/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-4">Real Questions Fintro Answers</h2>
            <p className="text-base font-mono text-muted-foreground">Daily decision value for founders</p>
          </div>

          <div className="grid md:grid-cols-2 gap-4 max-w-3xl mx-auto">
            {useCases.map((useCase, index) => (
              <div
                key={index}
                className="bg-background border border-primary/30 rounded-lg p-6 hover:border-primary/70 transition-all"
              >
                <p className="text-sm font-mono text-foreground">{useCase}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust & Credibility */}
      <section className="container mx-auto px-4 lg:px-8 py-20">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-display text-foreground mb-6">Built for Cash Survival</h2>
            <div className="space-y-4 max-w-2xl mx-auto">
              <div className="flex items-start gap-3 justify-center">
                <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                <p className="text-base font-mono text-muted-foreground text-left">
                  Built for founders who care about cash survival
                </p>
              </div>
              <div className="flex items-start gap-3 justify-center">
                <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                <p className="text-base font-mono text-muted-foreground text-left">
                  Designed using CFO-grade financial thinking
                </p>
              </div>
              <div className="flex items-start gap-3 justify-center">
                <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                <p className="text-base font-mono text-muted-foreground text-left">Agent-driven architecture</p>
              </div>
              <div className="flex items-start gap-3 justify-center">
                <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                <p className="text-base font-mono text-muted-foreground text-left">
                  Enterprise-grade security and data isolation
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="container mx-auto px-4 lg:px-8 py-20 bg-accent/30">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-display text-foreground mb-6">Join the Fintro Early Access</h2>
          <p className="text-base font-mono text-muted-foreground mb-4">
            We're onboarding a limited number of companies
          </p>
          <p className="text-lg font-mono text-foreground mb-8">Talk to the AI CFO</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/signup">
              <Button size="lg" className="bg-primary hover:bg-primary/90 h-12 px-8 font-mono">
                Request Early Access
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-background">
        <div className="container mx-auto px-4 lg:px-8 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="text-2xl font-display text-primary">FINTRO</div>
              <Badge variant="outline" className="uppercase text-xs border-primary/50">
                AI CFO
              </Badge>
            </div>
            <p className="text-xs font-mono text-muted-foreground">© 2025 Fintro. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
