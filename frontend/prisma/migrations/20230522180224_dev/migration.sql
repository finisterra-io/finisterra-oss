/*
  Warnings:

  - The primary key for the `aws_account_provider_group` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - Added the required column `awsRegion` to the `aws_account_provider_group` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "aws_account_provider_group" DROP CONSTRAINT "aws_account_provider_group_pkey",
ADD COLUMN     "awsRegion" TEXT NOT NULL,
ADD CONSTRAINT "aws_account_provider_group_pkey" PRIMARY KEY ("awsAccountId", "providerGroupId", "awsRegion");
