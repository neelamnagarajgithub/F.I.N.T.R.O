-- CreateTable
CREATE TABLE "Organization" (
    "org_id" BIGSERIAL NOT NULL,
    "org_name" TEXT NOT NULL,
    "industry" TEXT,
    "state" TEXT,
    "current_balance" DECIMAL(65,30),
    "annual_revenue_range" TEXT,
    "annual_revenue" DECIMAL(65,30) NOT NULL,
    "employee_count" INTEGER,
    "cashflow_type" TEXT,
    "status" TEXT NOT NULL DEFAULT 'active',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Organization_pkey" PRIMARY KEY ("org_id")
);

-- CreateTable
CREATE TABLE "Customer" (
    "customer_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "customer_name" TEXT,
    "credit_terms_days" INTEGER NOT NULL DEFAULT 30,
    "total_outstanding_ar" DECIMAL(65,30),
    "payment_reliability_score" DOUBLE PRECISION,
    "dso_days" INTEGER,
    "status" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Customer_pkey" PRIMARY KEY ("customer_id")
);

-- CreateTable
CREATE TABLE "Invoice" (
    "invoice_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "customer_id" BIGINT NOT NULL,
    "invoice_number" TEXT,
    "invoice_date" TIMESTAMP(3),
    "due_date" TIMESTAMP(3),
    "amount" DECIMAL(65,30) NOT NULL,
    "payment_status" TEXT,
    "paid_amount" DECIMAL(65,30),
    "remaining_amount" DECIMAL(65,30),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Invoice_pkey" PRIMARY KEY ("invoice_id")
);

-- CreateTable
CREATE TABLE "Bill" (
    "bill_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "bill_number" TEXT,
    "bill_date" TIMESTAMP(3),
    "due_date" TIMESTAMP(3),
    "amount" DECIMAL(65,30) NOT NULL,
    "expense_category" TEXT,
    "payment_status" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Bill_pkey" PRIMARY KEY ("bill_id")
);

-- CreateTable
CREATE TABLE "Payment" (
    "payment_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "payment_date" TIMESTAMP(3),
    "payment_amount" DECIMAL(65,30) NOT NULL,
    "payment_type" TEXT,
    "description" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Payment_pkey" PRIMARY KEY ("payment_id")
);

-- CreateTable
CREATE TABLE "CashflowAnalysis" (
    "analysis_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "analysis_date" TIMESTAMP(3),
    "current_balance" DECIMAL(65,30),
    "dso_days" DOUBLE PRECISION,
    "dpo_days" DOUBLE PRECISION,
    "liquidity_ratio" DOUBLE PRECISION,
    "cash_health_score" DOUBLE PRECISION,
    "cash_conversion_cycle" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CashflowAnalysis_pkey" PRIMARY KEY ("analysis_id")
);

-- CreateTable
CREATE TABLE "CashFlowForecast" (
    "forecast_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "forecast_date" TIMESTAMP(3),
    "predicted_balance" DECIMAL(65,30) NOT NULL,
    "confidence_95" DECIMAL(65,30),
    "confidence_5" DECIMAL(65,30),
    "model_version" TEXT,
    "mape" DOUBLE PRECISION,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CashFlowForecast_pkey" PRIMARY KEY ("forecast_id")
);

-- CreateTable
CREATE TABLE "Anomaly" (
    "anomaly_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "anomaly_type" TEXT,
    "severity" TEXT,
    "entity_type" TEXT,
    "entity_id" BIGINT,
    "detected_date" TIMESTAMP(3),
    "baseline_value" DECIMAL(65,30),
    "actual_value" DECIMAL(65,30),
    "is_resolved" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Anomaly_pkey" PRIMARY KEY ("anomaly_id")
);

-- CreateTable
CREATE TABLE "LiquidityCollision" (
    "collision_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "collision_date" TIMESTAMP(3),
    "deficit_amount" DECIMAL(65,30),
    "severity" TEXT,
    "expense_breakdown" JSONB,
    "is_resolved" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "LiquidityCollision_pkey" PRIMARY KEY ("collision_id")
);

-- CreateTable
CREATE TABLE "CollectionQueue" (
    "queue_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "customer_id" BIGINT NOT NULL,
    "invoice_id" BIGINT,
    "priority_rank" INTEGER,
    "priority_score" DOUBLE PRECISION,
    "days_overdue" INTEGER,
    "amount" DECIMAL(65,30),
    "success_probability" DOUBLE PRECISION,
    "action_taken" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CollectionQueue_pkey" PRIMARY KEY ("queue_id")
);

-- CreateTable
CREATE TABLE "ScenarioSimulation" (
    "scenario_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "scenario_name" TEXT,
    "scenario_date" TIMESTAMP(3),
    "levers_applied" JSONB,
    "impact_vs_base" DECIMAL(65,30),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ScenarioSimulation_pkey" PRIMARY KEY ("scenario_id")
);

-- CreateTable
CREATE TABLE "CopilotConversation" (
    "conversation_id" BIGSERIAL NOT NULL,
    "org_id" BIGINT NOT NULL,
    "question" TEXT NOT NULL,
    "response" TEXT,
    "confidence_score" DOUBLE PRECISION,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CopilotConversation_pkey" PRIMARY KEY ("conversation_id")
);

-- CreateIndex
CREATE INDEX "Invoice_org_id_invoice_date_idx" ON "Invoice"("org_id", "invoice_date" DESC);

-- CreateIndex
CREATE INDEX "Invoice_customer_id_idx" ON "Invoice"("customer_id");

-- CreateIndex
CREATE INDEX "Bill_org_id_due_date_idx" ON "Bill"("org_id", "due_date" ASC);

-- CreateIndex
CREATE INDEX "Payment_org_id_payment_date_idx" ON "Payment"("org_id", "payment_date" DESC);

-- CreateIndex
CREATE INDEX "CashFlowForecast_org_id_forecast_date_idx" ON "CashFlowForecast"("org_id", "forecast_date" ASC);

-- CreateIndex
CREATE INDEX "LiquidityCollision_org_id_collision_date_idx" ON "LiquidityCollision"("org_id", "collision_date" ASC);

-- AddForeignKey
ALTER TABLE "Customer" ADD CONSTRAINT "Customer_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Invoice" ADD CONSTRAINT "Invoice_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Invoice" ADD CONSTRAINT "Invoice_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "Customer"("customer_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Bill" ADD CONSTRAINT "Bill_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Payment" ADD CONSTRAINT "Payment_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CashflowAnalysis" ADD CONSTRAINT "CashflowAnalysis_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CashFlowForecast" ADD CONSTRAINT "CashFlowForecast_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Anomaly" ADD CONSTRAINT "Anomaly_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LiquidityCollision" ADD CONSTRAINT "LiquidityCollision_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CollectionQueue" ADD CONSTRAINT "CollectionQueue_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CollectionQueue" ADD CONSTRAINT "CollectionQueue_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "Customer"("customer_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ScenarioSimulation" ADD CONSTRAINT "ScenarioSimulation_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CopilotConversation" ADD CONSTRAINT "CopilotConversation_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "Organization"("org_id") ON DELETE RESTRICT ON UPDATE CASCADE;
