/*
  Warnings:

  - Added the required column `organizationId` to the `scan` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "scan" ADD COLUMN     "organizationId" INTEGER NOT NULL;

-- AddForeignKey
ALTER TABLE "scan" ADD CONSTRAINT "scan_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
