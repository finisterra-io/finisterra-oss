/*
  Warnings:

  - You are about to drop the column `branch` on the `git_repo` table. All the data in the column will be lost.
  - You are about to drop the column `path` on the `git_repo` table. All the data in the column will be lost.
  - Added the required column `branch` to the `aws_account_git_repo` table without a default value. This is not possible if the table is not empty.
  - Added the required column `path` to the `aws_account_git_repo` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "aws_account_git_repo" ADD COLUMN     "branch" TEXT NOT NULL,
ADD COLUMN     "path" TEXT NOT NULL;

-- AlterTable
ALTER TABLE "git_repo" DROP COLUMN "branch",
DROP COLUMN "path";
