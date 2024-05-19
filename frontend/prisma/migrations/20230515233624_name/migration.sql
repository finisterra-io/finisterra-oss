/*
  Warnings:

  - You are about to drop the column `name` on the `github_account` table. All the data in the column will be lost.
  - Added the required column `login` to the `github_account` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "github_account" DROP COLUMN "name",
ADD COLUMN     "login" TEXT NOT NULL;
