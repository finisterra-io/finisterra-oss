/*
  Warnings:

  - A unique constraint covering the columns `[gitrepoId,organizationId]` on the table `git_repo` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "git_repo_gitrepoId_organizationId_key" ON "git_repo"("gitrepoId", "organizationId");
