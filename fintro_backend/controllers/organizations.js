import { prisma } from "../lib/prisma.js";

export const getAllOrganizations = async (req, res) => {
  const orgs = await prisma.organization.findMany();
  res.json(orgs);
};

export const getOrganizationById = async (req, res) => {
  const { id } = req.params;
  const org = await prisma.organization.findUnique({ where: { org_id: Number(id) }});
  res.json(org);
};

export const getOrganizationSummary = async (req, res) => {
  const { id } = req.params;

  const totalCustomers = await prisma.customer.count({ where: { org_id: Number(id) }});
  const totalInvoices = await prisma.invoice.count({ where: { org_id: Number(id) }});
  const totalBills = await prisma.bill.count({ where: { org_id: Number(id) }});
  const totalPayments = await prisma.payment.count({ where: { org_id: Number(id) }});

  res.json({
    totalCustomers,
    totalInvoices,
    totalBills,
    totalPayments
  });
};
