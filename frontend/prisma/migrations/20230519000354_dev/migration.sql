/*
  Warnings:

  - A unique constraint covering the columns `[awsAccountId,gitRepoId,organizationId]` on the table `aws_account_git_repo` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "aws_account_git_repo_awsAccountId_gitRepoId_organizationId_key" ON "aws_account_git_repo"("awsAccountId", "gitRepoId", "organizationId");
