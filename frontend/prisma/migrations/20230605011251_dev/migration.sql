/*
  Warnings:

  - A unique constraint covering the columns `[code]` on the table `provider_group` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "provider_group_code_key" ON "provider_group"("code");
