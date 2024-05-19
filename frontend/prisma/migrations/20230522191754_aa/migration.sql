/*
  Warnings:

  - Added the required column `awsAccountId` to the `aws_account` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "aws_account" ADD COLUMN     "awsAccountId" INTEGER NOT NULL;
