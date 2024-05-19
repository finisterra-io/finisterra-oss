/*
  Warnings:

  - A unique constraint covering the columns `[organizationId,TerraformModuleId,root_resource_type,root_resource_name]` on the table `terraform_module_instance` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "terraform_module_instance_organizationId_TerraformModuleId__key" ON "terraform_module_instance"("organizationId", "TerraformModuleId", "root_resource_type", "root_resource_name");
