/*
  Warnings:

  - A unique constraint covering the columns `[login]` on the table `github_account` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "github_account_login_key" ON "github_account"("login");
