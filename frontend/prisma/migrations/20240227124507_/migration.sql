/*
  Warnings:

  - A unique constraint covering the columns `[stripeSubscriptionId]` on the table `subscription` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "subscription_stripeSubscriptionId_key" ON "subscription"("stripeSubscriptionId");
