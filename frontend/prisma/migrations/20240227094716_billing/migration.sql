-- AlterTable
ALTER TABLE "organization" ADD COLUMN     "billingEmail" TEXT,
ADD COLUMN     "currentUsage" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "pricePerAccount" DOUBLE PRECISION NOT NULL DEFAULT 190,
ADD COLUMN     "quota" INTEGER NOT NULL DEFAULT 1,
ADD COLUMN     "stripeCustomerId" TEXT;

-- CreateTable
CREATE TABLE "subscription" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "stripeSubscriptionId" TEXT NOT NULL,
    "pricePerAccount" DOUBLE PRECISION NOT NULL DEFAULT 190,
    "billingCycleStart" TIMESTAMP(3) NOT NULL,
    "billingCycleEnd" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "subscription_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Transaction" (
    "id" SERIAL NOT NULL,
    "subscriptionId" INTEGER NOT NULL,
    "type" TEXT NOT NULL,
    "amount" DOUBLE PRECISION NOT NULL,
    "stripeChargeId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Transaction_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "subscription" ADD CONSTRAINT "subscription_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Transaction" ADD CONSTRAINT "Transaction_subscriptionId_fkey" FOREIGN KEY ("subscriptionId") REFERENCES "subscription"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
