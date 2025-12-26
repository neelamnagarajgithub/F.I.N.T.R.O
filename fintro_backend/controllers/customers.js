import { prisma } from "../lib/prisma.js";
import { getDateFilter } from "../utils/DateFilter.js";
export const getCustomersByOrg = async (req, res) => {
  const { orgId } = req.params;
  const customers = await prisma.customer.findMany({ where: { org_id: Number(orgId) }});
  res.json(customers);
};

export const getCustomerById = async (req, res) => {
  const { id } = req.params;
  const customer = await prisma.customer.findUnique({ where: { customer_id: Number(id) }});
  res.json(customer);
};

const diffDays = (start, end) => {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return Math.max(Math.ceil(ms / (1000 * 60 * 60 * 24)), 0);
};


export const getCustomerFinancialMetrics = async (req, res) => {
  const { id } = req.params;
  const { from, to } = req.query;

  const invoices = await prisma.invoice.findMany({
    where: {
      customer_id: Number(id),
      ...getDateFilter(from, to, "invoice_date")
    },
    select: {
      amount: true,
      paid_amount: true,
      invoice_date: true
    }
  });

  if (!invoices.length) {
    return res.json({
      totalOutstanding: "0.00",
      dsoDays: 0
    });
  }

  let totalReceivable = 0;
  let totalSales = 0;
  let totalWeightedDays = 0;

  const today = new Date();

  for (const inv of invoices) {
    const amount = Number(inv.amount);
    const paid = Number(inv.paid_amount ?? 0);
    const outstanding = amount - paid;

    totalSales += amount;
    totalReceivable += outstanding;

    if (outstanding > 0) {
      const daysOutstanding = diffDays(inv.invoice_date, today);
      totalWeightedDays += daysOutstanding * outstanding;
    }
  }

  const dso =
    totalReceivable > 0
      ? totalWeightedDays / totalReceivable
      : 0;

  res.json({
    period: { from, to },
    invoicesCount: invoices.length,
    totalOutstanding: totalReceivable.toFixed(2),
    dsoDays: Math.round(dso)
  });
};

export const getCustomerSummaryByOrg = async (req, res) => {
  const { orgId } = req.params;
  const { from, to } = req.query;

  const invoices = await prisma.invoice.findMany({
    where: {
      org_id: Number(orgId),
      ...getDateFilter(from, to, "invoice_date")
    },
    include: {
      customer: {
        select: { customer_id: true }
      }
    }
  });

  const today = new Date();
  const map = new Map();

  for (const inv of invoices) {
    const cid = inv.customer.customer_id;

    if (!map.has(cid)) {
      map.set(cid, {
        customerId: cid,
        invoices: 0,
        totalBilled: 0,
        totalPaid: 0,
        outstanding: 0,
        weightedDays: 0
      });
    }

    const row = map.get(cid);

    const amount = Number(inv.amount);
    const paid = Number(inv.paid_amount ?? 0);
    const outstanding = amount - paid;

    row.invoices += 1;
    row.totalBilled += amount;
    row.totalPaid += paid;
    row.outstanding += outstanding;

    if (outstanding > 0) {
      const days = diffDays(inv.invoice_date, today);
      row.weightedDays += days * outstanding;
    }
  }

  const customers = Array.from(map.values()).map(c => {
    const dso =
      c.outstanding > 0 ? Math.round(c.weightedDays / c.outstanding) : 0;

    let risk = "low";
    if (dso > 60 || c.outstanding > c.totalBilled * 0.5) risk = "high";
    else if (dso > 30) risk = "medium";

    return {
      customerId: c.customerId,
      invoices: c.invoices,
      totalBilled: c.totalBilled.toFixed(2),
      totalPaid: c.totalPaid.toFixed(2),
      outstanding: c.outstanding.toFixed(2),
      dsoDays: dso,
      risk
    };
  });

  res.json({
    orgId: Number(orgId),
    period: { from, to },
    totalCustomers: customers.length,
    customers
  });
};
