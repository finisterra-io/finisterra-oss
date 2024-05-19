/*
  Warnings:

  - Added the required column `userId` to the `scan` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "scan" ADD COLUMN     "userId" INTEGER NOT NULL;

-- AddForeignKey
ALTER TABLE "scan" ADD CONSTRAINT "scan_userId_fkey" FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
