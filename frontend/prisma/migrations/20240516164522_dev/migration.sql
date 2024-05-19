/*
  Warnings:

  - You are about to drop the column `hidden` on the `api_key` table. All the data in the column will be lost.
  - You are about to drop the column `AccessKeyId` on the `aws_account` table. All the data in the column will be lost.
  - You are about to drop the column `SecretAccessKey` on the `aws_account` table. All the data in the column will be lost.
  - You are about to drop the column `SessionToken` on the `aws_account` table. All the data in the column will be lost.
  - You are about to drop the column `region` on the `aws_account` table. All the data in the column will be lost.
  - You are about to drop the column `currentOrganizationId` on the `user` table. All the data in the column will be lost.

*/
-- DropForeignKey
ALTER TABLE "user" DROP CONSTRAINT "user_currentOrganizationId_fkey";

-- AlterTable
ALTER TABLE "api_key" DROP COLUMN "hidden";

-- AlterTable
ALTER TABLE "aws_account" DROP COLUMN "AccessKeyId",
DROP COLUMN "SecretAccessKey",
DROP COLUMN "SessionToken",
DROP COLUMN "region";

-- AlterTable
ALTER TABLE "user" DROP COLUMN "currentOrganizationId",
ADD COLUMN     "organizationId" INTEGER;

-- AddForeignKey
ALTER TABLE "user" ADD CONSTRAINT "user_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;
