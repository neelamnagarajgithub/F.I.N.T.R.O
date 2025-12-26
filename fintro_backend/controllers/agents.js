import { prisma } from "../lib/prisma.js";

export const getOrgCashflow = async (req, res) => {
  const { orgId } = req.params;
  const inflows = await prisma.payment.aggregate({
    _sum: { payment_amount: true },
    where: { org_id: Number(orgId), payment_type: "inflow" }
  });
  const outflows = await prisma.payment.aggregate({
    _sum: { payment_amount: true },
    where: { org_id: Number(orgId), payment_type: "outflow" }
  });
  res.json({
    inflow: inflows._sum.payment_amount || 0,
    outflow: outflows._sum.payment_amount || 0,
    netCashflow: (inflows._sum.payment_amount || 0) - (outflows._sum.payment_amount || 0)
  });
};

export const getOrgRiskLevel = async (req, res) => {
  const { orgId } = req.params;
  const overdueInvoices = await prisma.invoice.count({
    where: { org_id: Number(orgId), payment_status: "open", due_date: { lt: new Date() } }
  });
  const riskLevel = overdueInvoices > 20 ? "High" : overdueInvoices > 5 ? "Medium" : "Low";
  res.json({ overdueInvoices, riskLevel });
};
