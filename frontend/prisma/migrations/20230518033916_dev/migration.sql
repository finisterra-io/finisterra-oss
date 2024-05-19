/*
  Warnings:

  - You are about to drop the column `branch` on the `git_repo` table. All the data in the column will be lost.
  - You are about to drop the column `name` on the `git_repo` table. All the data in the column will be lost.
  - Added the required column `branchId` to the `git_repo` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gitrepoId` to the `git_repo` table without a default value. This is not possible if the table is not empty.

*/
-- DropIndex
DROP INDEX "git_repo_name_key";

-- AlterTable
ALTER TABLE "git_repo" DROP COLUMN "branch",
DROP COLUMN "name",
ADD COLUMN     "branchId" INTEGER NOT NULL,
ADD COLUMN     "gitrepoId" INTEGER NOT NULL;
