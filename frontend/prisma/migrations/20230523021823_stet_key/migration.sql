/*
  Warnings:

  - Added the required column `stateKey` to the `workspace` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "workspace" ADD COLUMN     "stateKey" TEXT NOT NULL;
