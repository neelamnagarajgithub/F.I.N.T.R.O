#!/usr/bin/env node
/**
 * Supabase + Prisma seed script
 * Generates realistic financial data for CFO FIntro
 * 
 * - 50 organizations with HIGH INFLOWS (positive cashflow)
 * - 50 organizations with HIGH OUTFLOWS (negative cashflow)
 * - Realistic SMB financial metrics
 * - Current balance tracking
 */

import { prisma } from '../lib/prisma.js'

// ============================================================
// CONFIGURATION
// ============================================================

const INDUSTRIES = [
  "IT",
  "Manufacturing",
  "Retail",
  "Healthcare",
  "Finance",
  "Logistics",
  "RealEstate",
  "Consulting",
  "EdTech",
  "E-Commerce"
];

const STATES = ["Bangalore", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad"];

// SMB Revenue Ranges (Annual)
const REVENUE_RANGES = {
  SMALL: { min: 50_000_000, max: 250_000_000 },      // ₹5Cr - ₹25Cr
  MEDIUM: { min: 250_000_000, max: 1_000_000_000 },  // ₹25Cr - ₹100Cr
  LARGE: { min: 1_000_000_000, max: 5_000_000_000 }  // ₹100Cr - ₹500Cr
};

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const randFloat = (min, max) => Math.random() * (max - min) + min;
const randChoice = (arr) => arr[Math.floor(Math.random() * arr.length)];

const formatCurrency = (amount) => {
  if (amount >= 10_000_000) {
    return `₹${(amount / 10_000_000).toFixed(1)}Cr`;
  }
  return `₹${(amount / 100_000).toFixed(1)}L`;
};

// ============================================================
// ORGANIZATIONS
// ============================================================

async function seedOrganizations() {
  console.log("\n📊 Creating 100 organizations...");
  const orgs = [];

  // First 50: HIGH INFLOW (Positive Cashflow)
  console.log("  • 50 organizations with HIGH INFLOWS (positive cashflow)");
  for (let i = 1; i <= 50; i++) {
    const revenueRange = randChoice(Object.values(REVENUE_RANGES));
    const annualRevenue = rand(revenueRange.min, revenueRange.max);
    
    // High inflows: positive balance
    const currentBalance = rand(
      annualRevenue * 0.2,  // At least 20% of revenue
      annualRevenue * 0.5   // Up to 50% of revenue
    );

    const org = await prisma.organization.create({
      data: {
        org_name: `${randChoice(INDUSTRIES)} Solutions ${i}`,
        industry: randChoice(INDUSTRIES),
        state: randChoice(STATES),
        employee_count: rand(20, 300),
        annual_revenue_range: 
          annualRevenue <= 250_000_000 ? "Small (5-25Cr)" :
          annualRevenue <= 1_000_000_000 ? "Medium (25-100Cr)" :
          "Large (100-500Cr)",
        annual_revenue: annualRevenue,
        current_balance: currentBalance,
        cashflow_type: "inflow_positive"
      }
    });
    orgs.push(org);
    console.log(`    ✓ ${org.org_name}: ₹${formatCurrency(annualRevenue)}, Balance: ${formatCurrency(currentBalance)}`);
  }

  // Next 50: HIGH OUTFLOW (Negative Cashflow)
  console.log("  • 50 organizations with HIGH OUTFLOWS (negative cashflow)");
  for (let i = 51; i <= 100; i++) {
    const revenueRange = randChoice(Object.values(REVENUE_RANGES));
    const annualRevenue = rand(revenueRange.min, revenueRange.max);
    
    // High outflows: negative balance
    const currentBalance = rand(
      -annualRevenue * 0.5,  // -50% of revenue
      -annualRevenue * 0.1   // -10% of revenue
    );

    const org = await prisma.organization.create({
      data: {
        org_name: `${randChoice(INDUSTRIES)} Enterprises ${i - 50}`,
        industry: randChoice(INDUSTRIES),
        state: randChoice(STATES),
        employee_count: rand(20, 300),
        annual_revenue_range:
          annualRevenue <= 250_000_000 ? "Small (5-25Cr)" :
          annualRevenue <= 1_000_000_000 ? "Medium (25-100Cr)" :
          "Large (100-500Cr)",
        annual_revenue: annualRevenue,
        current_balance: currentBalance,
        cashflow_type: "outflow_negative"
      }
    });
    orgs.push(org);
    console.log(`    ✓ ${org.org_name}: ₹${formatCurrency(annualRevenue)}, Balance: ${formatCurrency(currentBalance)}`);
  }

  console.log(`✅ Created ${orgs.length} organizations\n`);
  return orgs;
}

// ============================================================
// CUSTOMERS (ACCOUNTS RECEIVABLE)
// ============================================================

async function seedCustomers(org, count = 15) {
  const customers = [];

  // Number of customers varies by org size
  const actualCount = org.annual_revenue > 500_000_000 ? rand(20, 30) : rand(10, 20);

  for (let i = 0; i < actualCount; i++) {
    // AR varies by annual revenue
    const arPercentage = randFloat(0.1, 0.4); // 10-40% of annual revenue
    const totalOutstandingAr = org.annual_revenue * arPercentage;

    const customer = await prisma.customer.create({
      data: {
        org_id: org.org_id,
        customer_name: `Customer ${String.fromCharCode(65 + i)} Ltd`,
        credit_terms_days: randChoice([15, 30, 45, 60, 90]),
        total_outstanding_ar: Math.round(totalOutstandingAr),
        payment_reliability_score: randFloat(0.4, 1.0),
        dso_days: rand(15, 90),
        status: "active"
      }
    });
    customers.push(customer);
  }

  return customers;
}

// ============================================================
// INVOICES (RECEIVABLES)
// ============================================================

async function seedInvoices(org, customers, invoiceCount = 40) {
  if (customers.length === 0) return;

  for (let i = 0; i < invoiceCount; i++) {
    const customer = randChoice(customers);
    const daysBack = rand(0, 90);
    const invoiceDate = new Date(Date.now() - daysBack * 86400000);
    const dueDate = new Date(invoiceDate);
    dueDate.setDate(dueDate.getDate() + customer.credit_terms_days);

    // Invoice amount: 5-50L per invoice
    const amount = rand(5_000_000, 50_000_000);

    // Payment status distribution
    let paymentStatus = "open";
    let paidAmount = 0;
    let remainingAmount = amount;

    const r = Math.random();
    if (r > 0.75) {
      // 25% fully paid
      paymentStatus = "paid";
      paidAmount = amount;
      remainingAmount = 0;
    } else if (r > 0.50) {
      // 25% partial
      paymentStatus = "partial";
      paidAmount = rand(Math.round(amount * 0.3), Math.round(amount * 0.7));
      remainingAmount = amount - paidAmount;
    }
    // else 50% open

    await prisma.invoice.create({
      data: {
        org_id: org.org_id,
        customer_id: customer.customer_id,
        invoice_number: `INV-${org.org_id}-${i + 1}`,
        invoice_date: invoiceDate,
        due_date: dueDate,
        amount: Math.round(amount),
        payment_status: paymentStatus,
        paid_amount: Math.round(paidAmount),
        remaining_amount: Math.round(remainingAmount)
      }
    });
  }
}

// ============================================================
// BILLS (ACCOUNTS PAYABLE)
// ============================================================

async function seedBills(org, billCount = 35) {
  const categories = [
    "payroll",
    "rent",
    "loan_emi",
    "vendor_payment",
    "utilities",
    "tax",
    "insurance",
    "maintenance"
  ];

  for (let i = 0; i < billCount; i++) {
    const daysBack = rand(0, 60);
    const billDate = new Date(Date.now() - daysBack * 86400000);
    const dueDate = new Date(billDate);
    dueDate.setDate(dueDate.getDate() + randChoice([7, 15, 30]));

    const category = randChoice(categories);
    
    // Bill amounts by category
    let billAmount;
    if (category === "payroll") {
      billAmount = rand(500_000, 50_000_000); // Large payroll bills
    } else if (category === "loan_emi") {
      billAmount = rand(100_000, 20_000_000);
    } else if (category === "rent") {
      billAmount = rand(100_000, 10_000_000);
    } else {
      billAmount = rand(10_000, 5_000_000);
    }

    // Payment status: 60% paid, 40% open
    const paymentStatus = Math.random() > 0.4 ? "paid" : "open";

    await prisma.bill.create({
      data: {
        org_id: org.org_id,
        bill_number: `BILL-${org.org_id}-${i + 1}`,
        bill_date: billDate,
        due_date: dueDate,
        amount: Math.round(billAmount),
        expense_category: category,
        payment_status: paymentStatus,
        vendor_name: `Vendor ${String.fromCharCode(65 + (i % 26))}`
      }
    });
  }
}

// ============================================================
// PAYMENTS (CASH FLOW)
// ============================================================

async function seedPayments(org, paymentCount = 50) {
  for (let i = 0; i < paymentCount; i++) {
    const daysBack = rand(0, 90);
    const paymentDate = new Date(Date.now() - daysBack * 86400000);

    // Payment type based on org cashflow type
    let paymentType;
    if (org.cashflow_type === "inflow_positive") {
      // 70% inflows, 30% outflows
      paymentType = Math.random() > 0.3 ? "inflow" : "outflow";
    } else {
      // 70% outflows, 30% inflows
      paymentType = Math.random() > 0.7 ? "inflow" : "outflow";
    }

    // Payment amount: 10L - 2Cr
    let paymentAmount = rand(10_000_000, 200_000_000);

    // Higher inflow payments for positive cashflow orgs
    if (org.cashflow_type === "inflow_positive" && paymentType === "inflow") {
      paymentAmount = rand(50_000_000, 200_000_000);
    }
    // Higher outflow payments for negative cashflow orgs
    else if (org.cashflow_type === "outflow_negative" && paymentType === "outflow") {
      paymentAmount = rand(50_000_000, 200_000_000);
    }

    const descriptions = [
      "Customer payment received",
      "Invoice payment",
      "Salary disbursal",
      "Vendor payment",
      "Loan repayment",
      "GST payment",
      "Insurance premium",
      "Equipment purchase"
    ];

    await prisma.payment.create({
      data: {
        org_id: org.org_id,
        payment_date: paymentDate,
        payment_amount: Math.round(paymentAmount),
        payment_type: paymentType,
        description: randChoice(descriptions),
        status: "completed"
      }
    });
  }
}

// ============================================================
// MAIN EXECUTION
// ============================================================

async function main() {
  try {
    console.log("\n" + "=".repeat(70));
    console.log("CFO FINTRO - SUPABASE DATA SEEDING SCRIPT");
    console.log("=".repeat(70));

    // Delete existing data
    console.log("\n🧹 Cleaning up existing data...");
    await prisma.payment.deleteMany({});
    await prisma.bill.deleteMany({});
    await prisma.invoice.deleteMany({});
    await prisma.customer.deleteMany({});
    await prisma.organization.deleteMany({});
    console.log("✅ Cleaned up\n");

    // Seed organizations (100 total)
    const orgs = await seedOrganizations();

    // Seed customers, invoices, bills, payments for each org
    console.log("📋 Creating customers, invoices, bills, and payments...\n");
    let orgCount = 0;

    for (const org of orgs) {
      orgCount++;
      
      // Customers
      const customers = await seedCustomers(org);

      // Invoices (AR)
      await seedInvoices(org, customers, 35);

      // Bills (AP)
      await seedBills(org, 30);

      // Payments
      await seedPayments(org, 45);

      const progressPercent = Math.round((orgCount / orgs.length) * 100);
      console.log(`[${progressPercent}%] ✓ ${org.org_name}`);
    }

    console.log("\n" + "=".repeat(70));
    console.log("✅ SEEDING COMPLETE!");
    console.log("=".repeat(70));
    console.log(`
📊 Summary:
   • Organizations: 100
     - 50 with HIGH INFLOWS (positive cashflow)
     - 50 with HIGH OUTFLOWS (negative cashflow)
   • Customers: ~2,500
   • Invoices: ~3,500
   • Bills: ~3,000
   • Payments: ~4,500

💰 Financial Ranges (SMB):
   • Small: ₹5Cr - ₹25Cr annual revenue
   • Medium: ₹25Cr - ₹100Cr annual revenue
   • Large: ₹100Cr - ₹500Cr annual revenue

✨ Features:
   ✓ Realistic payment distributions
   ✓ Current balance tracking
   ✓ Positive and negative cashflow scenarios
   ✓ Varied credit terms and DSO
   ✓ Realistic bill categories
   ✓ Invoice payment status distribution

🚀 Ready for risk assessment analysis!
    `);
    console.log("=".repeat(70) + "\n");

  } catch (error) {
    console.error("\n❌ Seeding error:", error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();