/*
  Warnings:

  - You are about to drop the `GithubAccount` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "GithubAccount" DROP CONSTRAINT "GithubAccount_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "git_repo" DROP CONSTRAINT "git_repo_githubAccountId_fkey";

-- DropTable
DROP TABLE "GithubAccount";

-- CreateTable
CREATE TABLE "github_account" (
    "id" SERIAL NOT NULL,
    "login" TEXT NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "installationId" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "github_account_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "github_account_login_key" ON "github_account"("login");

-- CreateIndex
CREATE UNIQUE INDEX "github_account_organizationId_key" ON "github_account"("organizationId");

-- CreateIndex
CREATE INDEX "organizationId" ON "github_account"("organizationId");

-- AddForeignKey
ALTER TABLE "github_account" ADD CONSTRAINT "github_account_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "git_repo" ADD CONSTRAINT "git_repo_githubAccountId_fkey" FOREIGN KEY ("githubAccountId") REFERENCES "github_account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
