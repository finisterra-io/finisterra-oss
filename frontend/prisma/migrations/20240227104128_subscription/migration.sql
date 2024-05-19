/*
  Warnings:

  - You are about to drop the `subscription` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "subscription" DROP CONSTRAINT "subscription_organizationId_fkey";

-- DropTable
DROP TABLE "subscription";

-- CreateTable
CREATE TABLE "Subscription" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "stripeSubscriptionId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Subscription_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "Subscription" ADD CONSTRAINT "Subscription_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
