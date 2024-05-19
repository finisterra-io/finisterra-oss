/*
  Warnings:

  - The primary key for the `api_key` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - The `id` column on the `api_key` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "api_key" DROP CONSTRAINT "api_key_pkey",
DROP COLUMN "id",
ADD COLUMN     "id" SERIAL NOT NULL,
ADD CONSTRAINT "api_key_pkey" PRIMARY KEY ("id");
