-- CreateEnum
CREATE TYPE "MembershipStatus" AS ENUM ('ACTIVE', 'INACTIVE');

-- AlterTable
ALTER TABLE "membership" ADD COLUMN     "membershipStatus" "MembershipStatus" NOT NULL DEFAULT 'ACTIVE';

-- AlterTable
ALTER TABLE "user" ADD COLUMN     "currentOrganizationId" INTEGER;

-- AddForeignKey
ALTER TABLE "user" ADD CONSTRAINT "user_currentOrganizationId_fkey" FOREIGN KEY ("currentOrganizationId") REFERENCES "organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;
