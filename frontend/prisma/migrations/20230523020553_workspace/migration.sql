/*
  Warnings:

  - You are about to drop the column `id_provider_group` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `state_backend` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the `aws_account_provider_group` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[awsAccountId,providerGroupId,awsRegion]` on the table `workspace` will be added. If there are existing duplicate values, this will fail.

*/
-- DropForeignKey
ALTER TABLE "aws_account_provider_group" DROP CONSTRAINT "aws_account_provider_group_awsAccountId_fkey";

-- DropForeignKey
ALTER TABLE "aws_account_provider_group" DROP CONSTRAINT "aws_account_provider_group_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "aws_account_provider_group" DROP CONSTRAINT "aws_account_provider_group_providerGroupId_fkey";

-- DropForeignKey
ALTER TABLE "workspace" DROP CONSTRAINT "workspace_id_provider_group_fkey";

-- AlterTable
ALTER TABLE "aws_state_config" ADD CONSTRAINT "aws_state_config_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "workspace" DROP COLUMN "id_provider_group",
DROP COLUMN "state_backend",
ADD COLUMN     "awsAccountId" INTEGER,
ADD COLUMN     "awsRegion" TEXT,
ADD COLUMN     "awsStateConfigId" INTEGER,
ADD COLUMN     "providerGroupId" INTEGER,
ADD COLUMN     "scanInterval" INTEGER NOT NULL DEFAULT 3600;

-- DropTable
DROP TABLE "aws_account_provider_group";

-- CreateIndex
CREATE UNIQUE INDEX "workspace_awsAccountId_providerGroupId_awsRegion_key" ON "workspace"("awsAccountId", "providerGroupId", "awsRegion");

-- AddForeignKey
ALTER TABLE "workspace" ADD CONSTRAINT "workspace_awsStateConfigId_fkey" FOREIGN KEY ("awsStateConfigId") REFERENCES "aws_state_config"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workspace" ADD CONSTRAINT "workspace_awsAccountId_fkey" FOREIGN KEY ("awsAccountId") REFERENCES "aws_account"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workspace" ADD CONSTRAINT "workspace_providerGroupId_fkey" FOREIGN KEY ("providerGroupId") REFERENCES "provider_group"("id") ON DELETE SET NULL ON UPDATE CASCADE;
