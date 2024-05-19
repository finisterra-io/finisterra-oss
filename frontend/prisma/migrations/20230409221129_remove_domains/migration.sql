/*
  Warnings:

  - You are about to drop the `Domain` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "Domain" DROP CONSTRAINT "Domain_organizationId_fkey";

-- DropTable
DROP TABLE "Domain";
