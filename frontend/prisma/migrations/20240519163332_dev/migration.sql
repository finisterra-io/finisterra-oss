/*
  Warnings:

  - A unique constraint covering the columns `[awsAccountId,region]` on the table `aws_account` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "aws_account_awsAccountId_region_key" ON "aws_account"("awsAccountId", "region");
