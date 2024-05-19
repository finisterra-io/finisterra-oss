/*
  Warnings:

  - You are about to drop the column `driftFixPR` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `gitPath` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `lastJobExecution` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `scannedTerraformPlan` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `stateKey` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `terraformPlan` on the `workspace` table. All the data in the column will be lost.
  - You are about to drop the column `terraformPlanBranch2Main` on the `workspace` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "workspace" DROP COLUMN "driftFixPR",
DROP COLUMN "gitPath",
DROP COLUMN "lastJobExecution",
DROP COLUMN "scannedTerraformPlan",
DROP COLUMN "stateKey",
DROP COLUMN "terraformPlan",
DROP COLUMN "terraformPlanBranch2Main";
