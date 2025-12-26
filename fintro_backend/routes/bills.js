import express from "express";
import { getBillsByOrg, getBillById, getBillsSummary } from "../controllers/bills.js";

const router = express.Router();

// Get all bills of an organization
router.get("/org/:orgId", getBillsByOrg);

// Get a single bill by ID
router.get("/:id", getBillById);

// Get bills summary (total amount, paid, due)
router.get("/org/:orgId/summary", getBillsSummary);

export default router;
