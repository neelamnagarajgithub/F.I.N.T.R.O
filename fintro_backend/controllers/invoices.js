import { prisma } from "../lib/prisma.js";

/**
 * Get all invoices for an organization
 * Optional query: ?from=YYYY-MM-DD&to=YYYY-MM-DD
 */
export const getInvoicesByOrg = async (req, res) => {
  const orgId = Number(req.params.orgId);
  const { from, to } = req.query;

  const where = { org_id: orgId };

  if (from || to) {
    where.invoice_date = {};
    if (from) where.invoice_date.gte = new Date(from);
    if (to) where.invoice_date.lte = new Date(to);
  }

  const invoices = await prisma.invoice.findMany({
    where,
    orderBy: { invoice_date: "desc" }
  });

  res.json({
    count: invoices.length,
    invoices
  });
};

/**
 * Get a single invoice by its ID
 */
export const getInvoiceById = async (req, res) => {
  const id = Number(req.params.id);
  const invoice = await prisma.invoice.findUnique({ where: { invoice_id: id } });
  res.json(invoice);
};

/**
 * Get invoice summary for an organization
 * Optional query: ?from=YYYY-MM-DD&to=YYYY-MM-DD
 */
export const getInvoicesSummary = async (req, res) => {
  const { orgId } = req.params;
  const { from, to } = req.query; // e.g., ?from=2025-12-01&to=2025-12-18

  const where = { org_id: Number(orgId) };

  if (from || to) {
    where.invoice_date = {};
    if (from) where.invoice_date.gte = new Date(from);
    if (to) where.invoice_date.lte = new Date(to);
  }

  const invoices = await prisma.invoice.findMany({
    where,
    select: {
      amount: true,
      paid_amount: true,
      remaining_amount: true
    }
  });

  let totalAmount = 0;
  let totalPaid = 0;
  let totalOutstanding = 0;

  for (const inv of invoices) {
    totalAmount += Number(inv.amount ?? 0);
    totalPaid += Number(inv.paid_amount ?? 0);
    totalOutstanding += Number(inv.remaining_amount ?? 0);
  }
  
  res.json({
    period: { from: from || null, to: to || null },
    totalInvoices: invoices.length,
    totalAmount: totalAmount.toFixed(2),
    totalPaid: totalPaid.toFixed(2),
    totalOutstanding: totalOutstanding.toFixed(2)
  });
};
