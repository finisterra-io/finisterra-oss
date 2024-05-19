/*
  Warnings:

  - Added the required column `code` to the `provider_group` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "provider_group" ADD COLUMN     "code" TEXT NOT NULL;
