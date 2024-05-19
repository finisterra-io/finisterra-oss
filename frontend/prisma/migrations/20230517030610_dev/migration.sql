/*
  Warnings:

  - A unique constraint covering the columns `[name]` on the table `git_repo` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `name` to the `git_repo` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "git_repo" ADD COLUMN     "name" TEXT NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "git_repo_name_key" ON "git_repo"("name");
