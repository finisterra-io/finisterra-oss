/*
  Warnings:

  - A unique constraint covering the columns `[name]` on the table `provider` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "provider_name_key" ON "provider"("name");
