-- AlterTable
ALTER TABLE "git_repo" ADD COLUMN     "terraformModuleInstanceId" INTEGER;

-- CreateTable
CREATE TABLE "terraform_module_instance" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "TerraformModuleId" INTEGER NOT NULL,
    "root_resource_type" TEXT NOT NULL,
    "root_resource_name" TEXT NOT NULL,
    "gitPath" TEXT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "description" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "terraform_module_instance_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "git_repo" ADD CONSTRAINT "git_repo_terraformModuleInstanceId_fkey" FOREIGN KEY ("terraformModuleInstanceId") REFERENCES "terraform_module_instance"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "terraform_module_instance" ADD CONSTRAINT "terraform_module_instance_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
