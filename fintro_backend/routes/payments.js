import express from "express";
import { getPaymentsByOrg, getPaymentById, getPaymentsSummaryByOrg } from "../controllers/payments.js";

const router = express.Router();

// Get all payments of an organization
router.get("/org/:orgId", getPaymentsByOrg);

// Get a single payment by ID
router.get("/:id", getPaymentById);

router.get("/org/:orgId/summary", getPaymentsSummaryByOrg); // Summary for org, optional ?from=&to=

export default router;
