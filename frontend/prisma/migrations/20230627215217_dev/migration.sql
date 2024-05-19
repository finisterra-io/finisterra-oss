/*
  Warnings:

  - A unique constraint covering the columns `[gitPath,organizationId]` on the table `terraform_module` will be added. If there are existing duplicate values, this will fail.

*/
-- DropIndex
DROP INDEX "terraform_module_organizationId_key";

-- CreateIndex
CREATE UNIQUE INDEX "terraform_module_gitPath_organizationId_key" ON "terraform_module"("gitPath", "organizationId");
