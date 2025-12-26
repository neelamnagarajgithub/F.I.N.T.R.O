import { prisma } from "../lib/prisma.js";

/**
 * GET /orgs/:orgId/bills
 */
export const getBillsByOrg = async (req, res) => {
  const orgId = Number(req.params.orgId);
  const { from, to } = req.query;

  const where = { org_id: orgId };

  if (from || to) {
    where.bill_date = {};
    if (from) where.bill_date.gte = new Date(from);
    if (to) where.bill_date.lte = new Date(to);
  }

  const bills = await prisma.bill.findMany({
    where,
    orderBy: { bill_date: "desc" }
  });

  res.json({
    count: bills.length,
    bills
  });
};

/**
 * GET /bills/:id
 */
export const getBillById = async (req, res) => {
  const id = Number(req.params.id);
  if (Number.isNaN(id)) {
    return res.status(400).json({ error: "Invalid bill id" });
  }

  const bill = await prisma.bill.findUnique({
    where: { bill_id: id }
  });

  res.json(bill);
};

/**
 * GET /orgs/:orgId/bills/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
 */
export const getBillsSummary = async (req, res) => {
  const orgId = Number(req.params.orgId);
  const { from, to } = req.query;

  if (Number.isNaN(orgId)) {
    return res.status(400).json({ error: "Invalid orgId" });
  }

  const dateFilter = {};
  if (from || to) {
    dateFilter.bill_date = {};
    if (from) dateFilter.bill_date.gte = new Date(from);
    if (to) dateFilter.bill_date.lte = new Date(to);
  }

  const bills = await prisma.bill.findMany({
    where: {
      org_id: orgId,
      ...dateFilter
    },
    select: {
      amount: true,
      payment_status: true
    }
  });

  let totalAmount = 0;
  let totalPaid = 0;

  for (const bill of bills) {
    const amount = Number(bill.amount ?? 0);
    totalAmount += amount;

    if (bill.payment_status === "paid") {
      totalPaid += amount;
    }
  }

  const totalDue = totalAmount - totalPaid;

  res.json({
    period: { from: from || null, to: to || null },
    totalBills: bills.length,
    totalAmount: totalAmount.toFixed(2),
    totalPaid: totalPaid.toFixed(2),
    totalDue: totalDue.toFixed(2)
  });
};
