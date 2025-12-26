import express from "express";
import { getOrgCashflow, getOrgRiskLevel } from "../controllers/agents.js";

const router = express.Router();

// Get cashflow summary for an organization
router.get("/org/:orgId/cashflow", getOrgCashflow);

// Get risk level for an organization (based on overdue invoices)
router.get("/org/:orgId/risk", getOrgRiskLevel);

export default router;
