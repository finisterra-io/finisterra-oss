/*
  Warnings:

  - The primary key for the `aws_state_config` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - A unique constraint covering the columns `[awsAccountId,organizationId,awsRegion]` on the table `aws_state_config` will be added. If there are existing duplicate values, this will fail.

*/
-- AlterTable
ALTER TABLE "aws_state_config" DROP CONSTRAINT "aws_state_config_pkey";

-- CreateIndex
CREATE UNIQUE INDEX "aws_state_config_awsAccountId_organizationId_awsRegion_key" ON "aws_state_config"("awsAccountId", "organizationId", "awsRegion");
