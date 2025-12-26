import { prisma } from "../lib/prisma.js";

// Get all payments for an organization
export const getPaymentsByOrg = async (req, res) => {
  const { orgId } = req.params;
  const { from, to } = req.query;

  const where = { org_id: Number(orgId) };
  if (from || to) {
    where.payment_date = {};
    if (from) where.payment_date.gte = new Date(from);
    if (to) where.payment_date.lte = new Date(to);
  }

  const payments = await prisma.payment.findMany({ where });
  res.json({
    period: { from: from || null, to: to || null },
    totalPayments: payments.length,
    payments
  });
};

// Get single payment by ID
export const getPaymentById = async (req, res) => {
  const { id } = req.params;
  const payment = await prisma.payment.findUnique({ where: { payment_id: Number(id) }});
  res.json(payment);
};

// Get payments summary for an organization
export const getPaymentsSummaryByOrg = async (req, res) => {
  const { orgId } = req.params;
  const { from, to } = req.query;

  const where = { org_id: Number(orgId) };
  if (from || to) {
    where.payment_date = {};
    if (from) where.payment_date.gte = new Date(from);
    if (to) where.payment_date.lte = new Date(to);
  }

  const payments = await prisma.payment.findMany({
    where,
    select: {
      payment_amount: true,
      payment_type: true
    }
  });

  let totalInflow = 0;
  let totalOutflow = 0;

  for (const p of payments) {
    if (p.payment_type === "inflow") totalInflow += Number(p.payment_amount ?? 0);
    else totalOutflow += Number(p.payment_amount ?? 0);
  }

  res.json({
    period: { from: from || null, to: to || null },
    totalPayments: payments.length,
    totalInflow: totalInflow.toFixed(2),
    totalOutflow: totalOutflow.toFixed(2),
    netCashflow: (totalInflow - totalOutflow).toFixed(2)
  });
};
