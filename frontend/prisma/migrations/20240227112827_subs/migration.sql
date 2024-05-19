/*
  Warnings:

  - You are about to drop the `Subscription` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "Subscription" DROP CONSTRAINT "Subscription_organizationId_fkey";

-- AlterTable
ALTER TABLE "organization" ADD COLUMN     "subscriptionActive" BOOLEAN NOT NULL DEFAULT false;

-- DropTable
DROP TABLE "Subscription";

-- CreateTable
CREATE TABLE "subscription" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "stripeSubscriptionId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "subscription_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "subscription" ADD CONSTRAINT "subscription_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
