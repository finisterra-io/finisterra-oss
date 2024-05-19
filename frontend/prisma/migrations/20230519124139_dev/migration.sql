/*
  Warnings:

  - Added the required column `organizationId` to the `tag` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "tag" ADD COLUMN     "organizationId" INTEGER NOT NULL;
