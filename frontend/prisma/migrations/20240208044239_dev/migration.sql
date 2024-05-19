/*
  Warnings:

  - You are about to drop the `resource` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `run` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `scan` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `terraform_module` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `terraform_module_instance` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "git_repo" DROP CONSTRAINT "git_repo_terraformModuleId_fkey";

-- DropForeignKey
ALTER TABLE "git_repo" DROP CONSTRAINT "git_repo_terraformModuleInstanceId_fkey";

-- DropForeignKey
ALTER TABLE "resource" DROP CONSTRAINT "resource_awsAccountId_fkey";

-- DropForeignKey
ALTER TABLE "resource" DROP CONSTRAINT "resource_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "resource" DROP CONSTRAINT "resource_workspaceId_fkey";

-- DropForeignKey
ALTER TABLE "run" DROP CONSTRAINT "run_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "run" DROP CONSTRAINT "run_workspaceId_fkey";

-- DropForeignKey
ALTER TABLE "scan" DROP CONSTRAINT "scan_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "scan" DROP CONSTRAINT "scan_workspaceId_fkey";

-- DropForeignKey
ALTER TABLE "terraform_module" DROP CONSTRAINT "terraform_module_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "terraform_module" DROP CONSTRAINT "terraform_module_providerGroupId_fkey";

-- DropForeignKey
ALTER TABLE "terraform_module_instance" DROP CONSTRAINT "terraform_module_instance_TerraformModuleId_fkey";

-- DropForeignKey
ALTER TABLE "terraform_module_instance" DROP CONSTRAINT "terraform_module_instance_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "terraform_module_instance" DROP CONSTRAINT "terraform_module_instance_workspaceId_fkey";

-- DropTable
DROP TABLE "resource";

-- DropTable
DROP TABLE "run";

-- DropTable
DROP TABLE "scan";

-- DropTable
DROP TABLE "terraform_module";

-- DropTable
DROP TABLE "terraform_module_instance";

-- DropEnum
DROP TYPE "RunStatus";

-- DropEnum
DROP TYPE "RunTrigger";

-- DropEnum
DROP TYPE "ScanStatus";

-- DropEnum
DROP TYPE "ScanTrigger";
