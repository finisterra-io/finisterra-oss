-- DropForeignKey
ALTER TABLE "github_account" DROP CONSTRAINT "github_account_organizationId_fkey";

-- AlterTable
ALTER TABLE "github_account" ALTER COLUMN "organizationId" DROP NOT NULL;

-- AddForeignKey
ALTER TABLE "github_account" ADD CONSTRAINT "github_account_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;
