/*
  Warnings:

  - You are about to drop the column `login` on the `github_account` table. All the data in the column will be lost.

*/
-- DropIndex
DROP INDEX "github_account_login_key";

-- AlterTable
ALTER TABLE "github_account" DROP COLUMN "login";
