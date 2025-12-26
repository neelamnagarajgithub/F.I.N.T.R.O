import express from "express";
import { getInvoicesByOrg, getInvoiceById, getInvoicesSummary } from "../controllers/invoices.js";

const router = express.Router();

// Get all invoices of an organization
router.get("/org/:orgId", getInvoicesByOrg);

// Get a single invoice by ID
router.get("/:id", getInvoiceById);

// Get invoices summary (total amount, total paid, outstanding)
router.get("/org/:orgId/summary", getInvoicesSummary);

export default router;
