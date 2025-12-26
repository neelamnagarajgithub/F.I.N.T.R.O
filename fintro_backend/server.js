BigInt.prototype.toJSON = function () {
  return this.toString();
};

import express from "express";
import dotenv from "dotenv";

import orgRoutes from "./routes/organizations.js";
import customerRoutes from "./routes/customers.js";
import invoiceRoutes from "./routes/invoices.js";
import billRoutes from "./routes/bills.js";
import paymentRoutes from "./routes/payments.js";
import agentRoutes from "./routes/agents.js";
import cors from "cors";

dotenv.config();
const app = express();
app.use(express.json());

const allowedOrgins =[
  "http://localhost:8000",
  "http://fintro.nagarajneelam.me",
  "http://localhost:4000"
];

app.use(cors({
  "origin":allowedOrgins,
  "methods":"GET,HEAD,PUT,PATCH,POST,DELETE",
  credentials:true,
}))
// Routes
app.use("/organizations", orgRoutes);
app.use("/customers", customerRoutes);
app.use("/invoices", invoiceRoutes);
app.use("/bills", billRoutes);
app.use("/payments", paymentRoutes);
app.use("/agents", agentRoutes);

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
