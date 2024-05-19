/*
  Warnings:

  - You are about to drop the `github_organization` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `github_user` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "github_organization" DROP CONSTRAINT "github_organization_githubUserId_fkey";

-- DropTable
DROP TABLE "github_organization";

-- DropTable
DROP TABLE "github_user";
