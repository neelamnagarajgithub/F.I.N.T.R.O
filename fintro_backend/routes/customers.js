import express from "express";
import { getCustomersByOrg, getCustomerById, getCustomerFinancialMetrics,getCustomerSummaryByOrg } from "../controllers/customers.js";

const router = express.Router();

// Get all customers of an organization
router.get("/org/:orgId", getCustomersByOrg);

// Get a single customer by ID
router.get("/:id", getCustomerById);

// Get financial metrics for a customer (DSO, total outstanding)
router.get("/:id/metrics", getCustomerFinancialMetrics);

// Get customer summary for an organization
router.get("/org/:orgId/summary", getCustomerSummaryByOrg);

export default router;
