"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Bullet } from "@/components/ui/bullet"
import Link from "next/link"
import { useState } from "react"
import { ArrowRight } from "lucide-react"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    // Simulate login
    setTimeout(() => {
      window.location.href = "/dashboard"
    }, 1000)
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-3 group">
            <div className="text-4xl font-display text-primary">FINTRO</div>
            <Badge variant="outline" className="uppercase text-xs border-primary/50 font-mono">
              AI CFO
            </Badge>
          </Link>
        </div>

        {/* Login Card */}
        <div className="bg-accent border border-border rounded-lg p-8">
          <div className="mb-6">
            <h1 className="text-2xl font-display text-foreground mb-2">Welcome Back</h1>
            <p className="text-sm font-mono text-muted-foreground">Access your financial command center</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-xs font-mono uppercase text-muted-foreground">
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-11 font-mono"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-xs font-mono uppercase text-muted-foreground">
                  Password
                </Label>
                <Link
                  href="/forgot-password"
                  className="text-xs font-mono text-muted-foreground hover:text-primary transition-colors"
                >
                  Forgot?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-11 font-mono"
              />
            </div>

            <Button type="submit" className="w-full h-11 bg-primary hover:bg-primary/90 font-mono" disabled={isLoading}>
              {isLoading ? (
                "LOGGING IN..."
              ) : (
                <>
                  LOG IN
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-border">
            <div className="flex items-center gap-3 justify-center">
              <Bullet variant="default" />
              <p className="text-sm font-mono text-muted-foreground">
                Don't have an account?{" "}
                <Link href="/signup" className="text-primary hover:text-primary/80 font-medium">
                  Request early access
                </Link>
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Bullet variant="success" />
            <p className="text-xs font-mono text-muted-foreground">Enterprise-grade security</p>
          </div>
          <p className="text-xs font-mono text-muted-foreground">
            <Link href="/privacy" className="text-primary hover:text-primary/80">
              Privacy Policy
            </Link>{" "}
            •{" "}
            <Link href="/terms" className="text-primary hover:text-primary/80">
              Terms
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
