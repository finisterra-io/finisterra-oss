/*
  Warnings:

  - Added the required column `commitHash` to the `run` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "run" ADD COLUMN     "commitHash" TEXT NOT NULL;
