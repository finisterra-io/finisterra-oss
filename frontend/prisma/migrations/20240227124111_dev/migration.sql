/*
  Warnings:

  - A unique constraint covering the columns `[stripeCustomerId]` on the table `organization` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "organization_stripeCustomerId_key" ON "organization"("stripeCustomerId");
