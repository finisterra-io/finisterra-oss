-- AlterEnum
ALTER TYPE "ScanTrigger" ADD VALUE 'DRIFT_FIXED';

-- AlterTable
ALTER TABLE "workspace" ADD COLUMN     "driftFixPR" TEXT;
