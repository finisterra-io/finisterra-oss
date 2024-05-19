/*
  Warnings:

  - You are about to drop the column `currentUsage` on the `organization` table. All the data in the column will be lost.
  - You are about to drop the column `pricePerAccount` on the `organization` table. All the data in the column will be lost.
  - You are about to drop the column `quota` on the `organization` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "organization" DROP COLUMN "currentUsage",
DROP COLUMN "pricePerAccount",
DROP COLUMN "quota";

-- CreateTable
CREATE TABLE "discount" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "type" TEXT NOT NULL,
    "value" DOUBLE PRECISION NOT NULL,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "discount_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "discount" ADD CONSTRAINT "discount_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
