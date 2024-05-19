/*
  Warnings:

  - You are about to drop the column `branchId` on the `git_repo` table. All the data in the column will be lost.
  - Added the required column `branch` to the `git_repo` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "git_repo" DROP COLUMN "branchId",
ADD COLUMN     "branch" TEXT NOT NULL;
