import express from "express";
import { getAllOrganizations, getOrganizationById, getOrganizationSummary } from "../controllers/organizations.js";

const router = express.Router();

// Get all organizations
router.get("/", getAllOrganizations);

// Get a single organization by ID
router.get("/:id", getOrganizationById);

// Get organization summary (customers, invoices, bills, payments)
router.get("/:id/summary", getOrganizationSummary);

export default router;
