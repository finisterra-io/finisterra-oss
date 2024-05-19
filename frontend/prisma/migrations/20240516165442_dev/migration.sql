/*
  Warnings:

  - You are about to drop the column `awsStateConfigId` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the `aws_state_config` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "aws_state_config" DROP CONSTRAINT "aws_state_config_awsAccountId_fkey";

-- DropForeignKey
ALTER TABLE "workspace" DROP CONSTRAINT "workspace_awsStateConfigId_fkey";

-- AlterTable
ALTER TABLE "workspace" DROP COLUMN "awsStateConfigId";

-- DropTable
DROP TABLE "aws_state_config";
