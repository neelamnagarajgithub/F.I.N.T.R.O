"use client";

import React, { useState } from "react";
import DashboardPageLayout from "@/components/dashboard/layout";
import DashboardCard from "@/components/dashboard/card";
import MonkeyIcon from "@/components/icons/monkey";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "https://cfo-backend-883163069340.us-central1.run.app";
const SNAPSHOT_KEY = "fintro_dashboard_snapshot";

export default function ExecutionPage() {
  const [orgId, setOrgId] = useState("315");
  const [message, setMessage] = useState("Will we face a cash crunch in 30 days?");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<any | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [savedHint, setSavedHint] = useState<string | null>(null);

  function extractReply(resp: any): string {
    if (!resp) return "No reply available.";
    // 1) structured.reply is preferred
    const structuredReply = resp?.structured?.reply;
    if (structuredReply && typeof structuredReply === "string") return structuredReply;

    // 2) try to parse llm_raw which may contain triple-backticked JSON
    const raw = resp.llm_raw ?? resp.llm;
    if (!raw) return "No reply available.";

    try {
      // extract JSON between ``` ``` if present
      const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
      const candidate = fenced ? fenced[1] : raw;

      // try parse JSON
      const parsed = JSON.parse(candidate);
      if (parsed?.reply && typeof parsed.reply === "string") return parsed.reply;

      // if parsed but no reply, maybe parsed is the whole structured object
      if (typeof parsed === "object") {
        // try common places
        if (parsed.reply && typeof parsed.reply === "string") return parsed.reply;
        if (parsed.structured?.reply && typeof parsed.structured.reply === "string") return parsed.structured.reply;
      }

      // fallback to candidate string (stripped)
      return String(candidate).trim();
    } catch (e) {
      // not JSON parseable, return raw text (trim)
      return String(raw).trim();
    }
  }

  async function sendChat() {
    setLoading(true);
    setError(null);
    setResponse(null);
    setSavedHint(null);

    try {
      const res = await fetch(`${API_BASE.replace(/\/$/, "")}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", accept: "application/json" },
        body: JSON.stringify({
          org_id: Number(orgId),
          message: message,
        }),
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Request failed (${res.status}) ${txt}`);
      }

      const json = await res.json();
      setResponse(json);

      // Auto-save full response into localStorage
      try {
        localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(json));
        setSavedHint("Snapshot saved locally.");
        window.setTimeout(() => setSavedHint(null), 2500);
      } catch (e) {
        console.error("Failed to save snapshot:", e);
        setSavedHint("Failed to save snapshot.");
        window.setTimeout(() => setSavedHint(null), 2500);
      }
    } catch (err: any) {
      setError(err?.message ?? String(err));
    } finally {
      setLoading(false);
    }
  }

  function saveSnapshot() {
    if (!response) return;
    try {
      localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(response));
      // small UX hint
      // eslint-disable-next-line no-alert
      alert("Snapshot saved locally.");
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert("Failed to save snapshot.");
      console.error(e);
    }
  }

  function loadSnapshot() {
    try {
      const s = localStorage.getItem(SNAPSHOT_KEY);
      if (!s) {
        // eslint-disable-next-line no-alert
        alert("No local snapshot found.");
        return;
      }
      const parsed = JSON.parse(s);
      setResponse(parsed);
      // eslint-disable-next-line no-alert
      alert("Loaded snapshot into view.");
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert("Failed to load snapshot.");
      console.error(e);
    }
  }

  function copyFullJSON() {
    if (!response) return;
    navigator.clipboard?.writeText(JSON.stringify(response, null, 2));
    // eslint-disable-next-line no-alert
    alert("Copied full JSON to clipboard.");
  }

  function copyReplyText() {
    const reply = extractReply(response);
    navigator.clipboard?.writeText(reply);
    // eslint-disable-next-line no-alert
    alert("Copied Copilot reply to clipboard.");
  }

  function pretty(x: any) {
    if (x == null) return "—";
    return typeof x === "string" ? x : JSON.stringify(x, null, 2);
  }

  const copilotReply = extractReply(response);

  return (
    <DashboardPageLayout
      header={{
        title: " Copilot",
        description: " ",
        icon: MonkeyIcon,
      }}
    >
      <div className="grid grid-cols-1 gap-6">
        <DashboardCard title="Fintro Copilot" intent="default">
          <div className="space-y-4">
            <div>
              <label className="text-xs uppercase text-muted-foreground">Org ID</label>
              <Input id="orgId" value={orgId} onChange={(e) => setOrgId(e.target.value)} className="mt-2" />
            </div>

            <div>
              <label className="text-xs uppercase text-muted-foreground">Query</label>
              <textarea
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full mt-2 p-2 bg-transparent border rounded-md min-h-[120px] resize-none"
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={sendChat} disabled={loading} className="flex-1">
                {loading ? "Sending..." : "Ask Copilot"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setOrgId("315");
                  setMessage("Will we face a cash crunch in 30 days?");
                }}
              >
                Reset
              </Button>
              <Button variant="ghost" onClick={loadSnapshot}>
                Load Snapshot
              </Button>
            </div>

            {error && <p className="text-sm text-destructive">Error: {error}</p>}

            {savedHint && <p className="text-sm text-muted-foreground">{savedHint}</p>}

            {response ? (
              <>
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <h4 className="text-sm uppercase text-muted-foreground mb-2">Copilot Reply</h4>
                    <div className="bg-accent p-4 rounded-md text-sm whitespace-pre-wrap">{copilotReply}</div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Button onClick={copyReplyText}>Copy Reply</Button>
                    <Button onClick={saveSnapshot} variant="outline">
                      Save Snapshot
                    </Button>
                    <Button onClick={copyFullJSON} variant="ghost">
                      Copy JSON
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setShowRaw((s) => !s);
                      }}
                    >
                      {showRaw ? "Hide Raw" : "Show Raw JSON"}
                    </Button>
                  </div>
                </div>

                {showRaw && (
                  <div className="mt-4">
                    <h4 className="text-sm uppercase text-muted-foreground mb-2">Full Response (raw)</h4>
                    <pre className="bg-accent p-3 rounded-md max-h-64 overflow-auto text-xs">{pretty(response)}</pre>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">No response yet. Ask Copilot to send a request.</p>
            )}
          </div>
        </DashboardCard>
      </div>
    </DashboardPageLayout>
  );
}