/*
  Warnings:

  - Added the required column `organizationId` to the `aws_account_git_repo` table without a default value. This is not possible if the table is not empty.
  - Added the required column `organizationId` to the `git_repo` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "aws_account_git_repo" ADD COLUMN     "organizationId" INTEGER NOT NULL;

-- AlterTable
ALTER TABLE "git_repo" ADD COLUMN     "organizationId" INTEGER NOT NULL;
