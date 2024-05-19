-- AlterTable
ALTER TABLE "aws_account" ADD COLUMN     "enabled" BOOLEAN NOT NULL DEFAULT true;

-- AlterTable
ALTER TABLE "workspace" ADD COLUMN     "enabled" BOOLEAN NOT NULL DEFAULT true;
