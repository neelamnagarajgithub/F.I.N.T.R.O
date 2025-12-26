"use client";

import * as React from "react";
import { XAxis, YAxis, CartesianGrid, Area, AreaChart } from "recharts";

import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import mockDataJson from "@/mock.json";
import { Bullet } from "@/components/ui/bullet";
import type { MockData } from "@/types/dashboard";

const mockData = mockDataJson as MockData;

type ChartDataPoint = {
  date: string;
  predicted_balance: number;
  inflow: number;
  outflow: number;
};

const chartConfig = {
  predicted_balance: {
    label: "Predicted Balance",
    color: "var(--chart-1)",
  },
  inflow: {
    label: "Avg Inflow",
    color: "var(--chart-2)",
  },
  outflow: {
    label: "Avg Outflow",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig;

/**
 * Props:
 * - orgId: optional org id to fetch data for (defaults to 315)
 * - horizonDays: how many days of /cashflow to request (default 30)
 *
 * This component runs client-side fetches and merges forecast + cashflow into
 * a combined series. If the backend is unreachable, it falls back to mock data.
 */
export default function DashboardChart({
  orgId = "315",
  horizonDays = 30,
}: {
  orgId?: string;
  horizonDays?: number;
}) {
  const [activeTab, setActiveTab] = React.useState<"week" | "month" | "year">(
    "week"
  );
  const [data, setData] = React.useState<ChartDataPoint[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const handleTabChange = (value: string) => {
    if (value === "week" || value === "month" || value === "year") {
      setActiveTab(value as "week" | "month" | "year");
    }
  };

  const formatYAxisValue = (value: number) => {
    if (value === 0) {
      return "";
    }

    if (Math.abs(value) >= 10000000) {
      return `${(value / 10000000).toFixed(0)}Cr`;
    } else if (Math.abs(value) >= 100000) {
      return `${(value / 100000).toFixed(0)}L`;
    } else if (Math.abs(value) >= 1000) {
      return `${(value / 1000).toFixed(0)}K`;
    }
    return value.toString();
  };

  // Format date to short label for X axis, e.g. "04 Dec"
  const formatDateLabel = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
      });
    } catch {
      return iso;
    }
  };

  React.useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    // Prepare POST body for /cashflow: last `horizonDays` days
    const end = new Date();
    const start = new Date(end);
    start.setDate(end.getDate() - (horizonDays - 1));

    const period_start = start.toISOString().slice(0, 10); // YYYY-MM-DD
    const period_end = end.toISOString().slice(0, 10); // YYYY-MM-DD

    // POST /cashflow with JSON body (org_id numeric as in your example)
    const cashflowFetch = fetch("https://cfo-backend-883163069340.us-central1.run.app/cashflow", {
      method: "POST",
      headers: { "Content-Type": "application/json", accept: "application/json" },
      body: JSON.stringify({
        org_id: Number(orgId),
        period_start,
        period_end,
      }),
      cache: "no-store",
    }).then(async (res) => {
      if (!res.ok) throw new Error(`cashflow fetch failed (${res.status})`);
      return res.json();
    });

    const forecastFetch = fetch(
      `https://cfo-backend-883163069340.us-central1.run.app/forecast?org_id=${encodeURIComponent(orgId)}`,
      {
        method: "GET",
        cache: "no-store",
      }
    ).then(async (res) => {
      if (!res.ok) throw new Error(`forecast fetch failed (${res.status})`);
      return res.json();
    });

    Promise.allSettled([forecastFetch, cashflowFetch])
      .then((results) => {
        if (!mounted) return;
        const [forecastRes, cashflowRes] = results;

        // If both failed, fallback to mock data
        if (
          forecastRes.status === "rejected" &&
          cashflowRes.status === "rejected"
        ) {
          const fallback = useMockSeries();
          setData(fallback.week);
          setError(
            "Unable to reach backend. Showing mock data. Check https://cfo-backend-883163069340.us-central1.run.app."
          );
          return;
        }

        // Extract forecast points
        let forecastPoints: {
          date: string;
          predicted_balance: number;
          avg_inflow?: number;
          avg_outflow?: number;
        }[] = [];

        if (forecastRes.status === "fulfilled" && forecastRes.value) {
          const fv = forecastRes.value;
          if (Array.isArray(fv.forecast)) {
            forecastPoints = fv.forecast.map((p: any) => ({
              date: p.date,
              predicted_balance: Number(p.predicted_balance ?? 0),
              avg_inflow: Number(p.avg_inflow ?? 0),
              avg_outflow: Number(p.avg_outflow ?? 0),
            }));
          } else if (Array.isArray(fv)) {
            forecastPoints = fv.map((p: any) => ({
              date: p.date,
              predicted_balance: Number(p.predicted_balance ?? 0),
              avg_inflow: Number(p.avg_inflow ?? 0),
              avg_outflow: Number(p.avg_outflow ?? 0),
            }));
          } else if (Array.isArray(fv?.forecast?.data)) {
            // defensive
            forecastPoints = fv.forecast.data.map((p: any) => ({
              date: p.date,
              predicted_balance: Number(p.predicted_balance ?? 0),
              avg_inflow: Number(p.avg_inflow ?? 0),
              avg_outflow: Number(p.avg_outflow ?? 0),
            }));
          }
        }

        // Aggregate cashflow payments per date into inflow/outflow
        const cashflowByDate: Record<
          string,
          { inflow: number; outflow: number }
        > = {};
        if (cashflowRes.status === "fulfilled" && cashflowRes.value) {
          const cf = cashflowRes.value;
          // Accept multiple field names: payments OR payments array under top-level
          const payments =
            Array.isArray(cf.payments) && cf.payments.length
              ? cf.payments
              : Array.isArray(cf?.payments)
              ? cf.payments
              : Array.isArray(cf?.payments_list)
              ? cf.payments_list
              : [];

          // If endpoint gave a flat payments array at top-level (defensive)
          const flatPayments =
            payments.length > 0 ? payments : Array.isArray(cf) ? cf : [];

          for (const p of flatPayments) {
            const date =
              (p.date ?? p.payment_date ?? p.paymentDate ?? p.timestamp ?? "")
                .slice(0, 10) || null;
            if (!date) continue;
            const amt = Number(
              p.amount ?? p.payment_amount ?? p.paymentAmount ?? 0
            );
            const type = (p.type ?? p.payment_type ?? p.paymentType ?? "")
              .toString()
              .toLowerCase();
            const isDebit =
              p.is_debit === true ||
              type === "outflow" ||
              type === "debit" ||
              (typeof p.amount === "number" && p.amount < 0) ||
              (typeof p.payment_amount === "number" && p.payment_amount < 0);
            if (!cashflowByDate[date]) cashflowByDate[date] = { inflow: 0, outflow: 0 };
            if (isDebit) cashflowByDate[date].outflow += Math.abs(amt);
            else cashflowByDate[date].inflow += Math.abs(amt);
          }

          // If the endpoint also returned pre-aggregated inflows/outflows and no payments,
          // use those to fill a single day (fallback)
          if (flatPayments.length === 0 && (cf.inflows || cf.outflows)) {
            // spread them to the end date so chart still shows numbers
            const singleDate = period_end;
            if (!cashflowByDate[singleDate]) cashflowByDate[singleDate] = { inflow: 0, outflow: 0 };
            cashflowByDate[singleDate].inflow += Number(cf.inflows ?? cf.total_inflows ?? 0);
            cashflowByDate[singleDate].outflow += Number(cf.outflows ?? cf.total_outflows ?? 0);
          }
        }

        // Merge dates from forecast + cashflow
        const dateSet = new Set<string>();
        forecastPoints.forEach((p) => dateSet.add((p.date ?? "").slice(0, 10)));
        Object.keys(cashflowByDate).forEach((d) => dateSet.add(d));

        const merged: ChartDataPoint[] = Array.from(dateSet)
          .filter(Boolean)
          .sort((a, b) => new Date(a).getTime() - new Date(b).getTime())
          .map((d) => {
            const fp = forecastPoints.find((p) => (p.date ?? "").slice(0, 10) === d);
            const cash = cashflowByDate[d] ?? { inflow: 0, outflow: 0 };
            return {
              date: d,
              predicted_balance: fp?.predicted_balance ?? 0,
              inflow: fp?.avg_inflow ?? cash.inflow ?? 0,
              outflow: fp?.avg_outflow ?? cash.outflow ?? 0,
            };
          });

        // If merged is empty, fallback to mock
        if (merged.length === 0) {
          const fallback = useMockSeries();
          setData(fallback.week);
          setError("No data returned; showing mock chart.");
          return;
        }

        setData(merged);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(String(err));
        const fallback = useMockSeries();
        setData(fallback.week);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [orgId, horizonDays]);

  const renderChart = (series: ChartDataPoint[]) => {
    return (
      <div className="bg-accent rounded-lg p-3">
        <ChartContainer className="md:aspect-[3/1] w-full" config={chartConfig}>
          <AreaChart
            accessibilityLayer
            data={series.map((s) => ({ ...s, date: formatDateLabel(s.date) }))}
            margin={{
              left: -12,
              right: 12,
              top: 12,
              bottom: 12,
            }}
          >
            <defs>
              <linearGradient id="fillPredicted" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-predicted_balance)" stopOpacity={0.8} />
                <stop offset="95%" stopColor="var(--color-predicted_balance)" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="fillInflow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-inflow)" stopOpacity={0.8} />
                <stop offset="95%" stopColor="var(--color-inflow)" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="fillOutflow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-outflow)" stopOpacity={0.8} />
                <stop offset="95%" stopColor="var(--color-outflow)" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid
              horizontal={false}
              strokeDasharray="8 8"
              strokeWidth={2}
              stroke="var(--muted-foreground)"
              opacity={0.3}
            />
            <XAxis
              dataKey="date"
              tickLine={false}
              tickMargin={12}
              strokeWidth={1.5}
              className="uppercase text-sm fill-muted-foreground"
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={0}
              tickCount={6}
              className="text-sm fill-muted-foreground"
              tickFormatter={formatYAxisValue}
              domain={["auto", "auto"]}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent indicator="dot" className="min-w-[200px] px-4 py-3" />
              }
            />
            <Area
              dataKey="predicted_balance"
              type="linear"
              fill="url(#fillPredicted)"
              fillOpacity={0.25}
              stroke="var(--color-predicted_balance)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Area
              dataKey="inflow"
              type="linear"
              fill="url(#fillInflow)"
              fillOpacity={0.2}
              stroke="var(--color-inflow)"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
            <Area
              dataKey="outflow"
              type="linear"
              fill="url(#fillOutflow)"
              fillOpacity={0.15}
              stroke="var(--color-outflow)"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
          </AreaChart>
        </ChartContainer>
      </div>
    );
  };

  return (
    <Tabs
      value={activeTab}
      onValueChange={handleTabChange}
      className="max-md:gap-4"
    >
      <div className="flex items-center justify-between mb-4 max-md:contents">
        <TabsList className="max-md:w-full">
          <TabsTrigger value="week">WEEK</TabsTrigger>
          <TabsTrigger value="month">MONTH</TabsTrigger>
          <TabsTrigger value="year">YEAR</TabsTrigger>
        </TabsList>
        <div className="flex items-center gap-6 max-md:order-1">
          {Object.entries(chartConfig).map(([key, value]) => (
            <ChartLegend key={key} label={value.label} color={value.color} />
          ))}
        </div>
      </div>

      <TabsContent value="week" className="space-y-4">
        {loading && (
          <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
            Loading chart...
          </div>
        )}
        {!loading && error && (
          <div className="text-sm text-destructive mb-2">{error}</div>
        )}
        {!loading && data && renderChart(filterSeriesForTab(data, "week"))}
      </TabsContent>

      <TabsContent value="month" className="space-y-4">
        {!loading && data && renderChart(filterSeriesForTab(data, "month"))}
      </TabsContent>

      <TabsContent value="year" className="space-y-4">
        {!loading && data && renderChart(filterSeriesForTab(data, "year"))}
      </TabsContent>
    </Tabs>
  );
}

export const ChartLegend = ({
  label,
  color,
}: {
  label: string;
  color: string;
}) => {
  return (
    <div className="flex items-center gap-2 uppercase">
      <Bullet style={{ backgroundColor: color }} className="rotate-45" />
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
    </div>
  );
};

/* ---------- Helpers ---------- */

function filterSeriesForTab(
  series: ChartDataPoint[],
  tab: "week" | "month" | "year"
) {
  if (tab === "week") {
    return series.slice(-7);
  }
  if (tab === "month") {
    return series.slice(-30);
  }
  return series; // year -> all available
}

function useMockSeries() {
  // Build a compatible ChartDataPoint[] from mockData if present
  // Try to map mockData.chartData.week which had spendings/sales/coffee
  try {
    const week = (mockData.chartData?.week ?? []).map((d: any) => ({
      date: d.date,
      predicted_balance:
        Number(d.sales ?? 0) - Number(d.spendings ?? 0) + Number(d.coffee ?? 0),
      inflow: Number(d.sales ?? 0),
      outflow: Number(d.spendings ?? 0),
    }));
    return { week, month: week, year: week };
  } catch {
    return { week: [], month: [], year: [] };
  }
}
