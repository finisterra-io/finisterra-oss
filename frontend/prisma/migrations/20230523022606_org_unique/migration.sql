/*
  Warnings:

  - A unique constraint covering the columns `[awsAccountId,providerGroupId,awsRegion,organizationId]` on the table `workspace` will be added. If there are existing duplicate values, this will fail.

*/
-- DropIndex
DROP INDEX "workspace_awsAccountId_providerGroupId_awsRegion_key";

-- CreateIndex
CREATE UNIQUE INDEX "workspace_awsAccountId_providerGroupId_awsRegion_organizati_key" ON "workspace"("awsAccountId", "providerGroupId", "awsRegion", "organizationId");
