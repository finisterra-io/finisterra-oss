/*
  Warnings:

  - You are about to drop the `github_account` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "git_repo" DROP CONSTRAINT "git_repo_githubAccountId_fkey";

-- DropForeignKey
ALTER TABLE "github_account" DROP CONSTRAINT "github_account_organizationId_fkey";

-- DropTable
DROP TABLE "github_account";

-- CreateTable
CREATE TABLE "GithubAccount" (
    "id" SERIAL NOT NULL,
    "login" TEXT NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "installationId" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "GithubAccount_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "GithubAccount_login_key" ON "GithubAccount"("login");

-- CreateIndex
CREATE UNIQUE INDEX "GithubAccount_organizationId_key" ON "GithubAccount"("organizationId");

-- CreateIndex
CREATE INDEX "organizationId" ON "GithubAccount"("organizationId");

-- AddForeignKey
ALTER TABLE "GithubAccount" ADD CONSTRAINT "GithubAccount_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "git_repo" ADD CONSTRAINT "git_repo_githubAccountId_fkey" FOREIGN KEY ("githubAccountId") REFERENCES "GithubAccount"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
