/*
  Warnings:

  - You are about to drop the column `userId` on the `scan` table. All the data in the column will be lost.

*/
-- DropForeignKey
ALTER TABLE "scan" DROP CONSTRAINT "scan_userId_fkey";

-- AlterTable
ALTER TABLE "scan" DROP COLUMN "userId";
