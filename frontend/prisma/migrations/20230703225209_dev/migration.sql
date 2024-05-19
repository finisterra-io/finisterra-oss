/*
  Warnings:

  - You are about to drop the column `root_resource_name` on the `terraform_module` table. All the data in the column will be lost.
  - You are about to drop the column `root_resource_type` on the `terraform_module` table. All the data in the column will be lost.
  - You are about to drop the column `root_resource_name` on the `terraform_module_instance` table. All the data in the column will be lost.
  - You are about to drop the column `root_resource_type` on the `terraform_module_instance` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[organizationId,TerraformModuleId,resource_type,resource_name]` on the table `terraform_module_instance` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `module_instance` to the `terraform_module_instance` table without a default value. This is not possible if the table is not empty.
  - Added the required column `resource_name` to the `terraform_module_instance` table without a default value. This is not possible if the table is not empty.
  - Added the required column `resource_type` to the `terraform_module_instance` table without a default value. This is not possible if the table is not empty.

*/
-- DropIndex
DROP INDEX "terraform_module_instance_organizationId_TerraformModuleId__key";

-- AlterTable
ALTER TABLE "terraform_module" DROP COLUMN "root_resource_name",
DROP COLUMN "root_resource_type";

-- AlterTable
ALTER TABLE "terraform_module_instance" DROP COLUMN "root_resource_name",
DROP COLUMN "root_resource_type",
ADD COLUMN     "module_instance" TEXT NOT NULL,
ADD COLUMN     "resource_name" TEXT NOT NULL,
ADD COLUMN     "resource_type" TEXT NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "terraform_module_instance_organizationId_TerraformModuleId__key" ON "terraform_module_instance"("organizationId", "TerraformModuleId", "resource_type", "resource_name");
