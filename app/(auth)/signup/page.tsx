"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Bullet } from "@/components/ui/bullet"
import Link from "next/link"
import { useState } from "react"
import { ArrowRight } from "lucide-react"

export default function SignupPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    password: "",
  })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agreedToTerms) return

    setIsLoading(true)
    // Simulate signup
    setTimeout(() => {
      window.location.href = "/dashboard"
    }, 1000)
  }

  const benefits = [
    "Real-time cash visibility",
    "AI-powered runway forecasting",
    "Autonomous risk detection",
    "Proactive financial intelligence",
  ]

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-6xl grid lg:grid-cols-2 gap-12 items-center">
        {/* Left Side - Form */}
        <div>
          {/* Logo */}
          <div className="mb-8">
            <Link href="/" className="inline-flex items-center gap-3 group">
              <div className="text-4xl font-display text-primary">FINTRO</div>
              <Badge variant="outline" className="uppercase text-xs border-primary/50 font-mono">
                AI CFO
              </Badge>
            </Link>
          </div>

          {/* Signup Card */}
          <div className="bg-accent border border-border rounded-lg p-8">
            <div className="mb-6">
              <h1 className="text-2xl font-display text-foreground mb-2">Request Early Access</h1>
              <p className="text-sm font-mono text-muted-foreground">Join the autonomous CFO revolution</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-xs font-mono uppercase text-muted-foreground">
                  Full Name
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  className="h-11 font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-mono uppercase text-muted-foreground">
                  Work Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  className="h-11 font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="company" className="text-xs font-mono uppercase text-muted-foreground">
                  Company Name
                </Label>
                <Input
                  id="company"
                  type="text"
                  placeholder="Acme Inc."
                  value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  required
                  className="h-11 font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-mono uppercase text-muted-foreground">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Create a strong password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  className="h-11 font-mono"
                />
                <p className="text-xs font-mono text-muted-foreground">Minimum 8 characters</p>
              </div>

              <div className="flex items-start gap-3 pt-2">
                <Checkbox
                  id="terms"
                  checked={agreedToTerms}
                  onCheckedChange={(checked) => setAgreedToTerms(checked as boolean)}
                  className="mt-0.5"
                />
                <label htmlFor="terms" className="text-xs font-mono text-muted-foreground leading-relaxed">
                  I agree to the{" "}
                  <Link href="/terms" className="text-primary hover:text-primary/80">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className="text-primary hover:text-primary/80">
                    Privacy Policy
                  </Link>
                </label>
              </div>

              <Button
                type="submit"
                className="w-full h-11 bg-primary hover:bg-primary/90 font-mono"
                disabled={isLoading || !agreedToTerms}
              >
                {isLoading ? (
                  "CREATING ACCOUNT..."
                ) : (
                  <>
                    REQUEST ACCESS
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-border">
              <div className="flex items-center gap-3 justify-center">
                <Bullet variant="default" />
                <p className="text-sm font-mono text-muted-foreground">
                  Already have an account?{" "}
                  <Link href="/login" className="text-primary hover:text-primary/80 font-medium">
                    Log in
                  </Link>
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Benefits */}
        <div className="hidden lg:block">
          <div className="bg-accent/50 border border-primary/30 rounded-lg p-8">
            <h2 className="text-3xl font-display text-foreground mb-2">Why Fintro?</h2>
            <p className="text-sm font-mono text-muted-foreground mb-6">
              Autonomous AI that behaves like a CFO, not software
            </p>

            <div className="space-y-4 mb-8">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start gap-3">
                  <Bullet variant="success" className="mt-1" />
                  <span className="text-sm font-mono text-foreground">{benefit}</span>
                </div>
              ))}
            </div>

            <div className="bg-background border border-border rounded-lg p-6">
              <div className="flex items-start gap-3 mb-4">
                <Bullet variant="primary" className="mt-1" />
                <p className="text-sm font-mono text-foreground italic">
                  "Fintro is not a dashboard. It's an autonomous financial decision engine that tells us what to do
                  before money runs out."
                </p>
              </div>
              <div className="flex items-center gap-3 ml-6">
                <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center text-sm font-display">
                  JD
                </div>
                <div>
                  <p className="text-sm font-mono font-medium text-foreground">Jane Doe</p>
                  <p className="text-xs font-mono text-muted-foreground">Founder, TechCorp</p>
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-accent rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Bullet variant="success" />
                <p className="text-xs font-mono uppercase text-muted-foreground">Early Access Benefits</p>
              </div>
              <p className="text-xs font-mono text-muted-foreground ml-5">
                Limited onboarding • Priority support • Founder access • Exclusive roadmap input
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
