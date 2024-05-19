/*
  Warnings:

  - Added the required column `name` to the `git_repo` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "git_repo" ADD COLUMN     "name" TEXT NOT NULL;
