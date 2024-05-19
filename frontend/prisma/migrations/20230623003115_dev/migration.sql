-- AlterTable
ALTER TABLE "git_repo" ADD COLUMN     "terraformModuleId" INTEGER;

-- CreateTable
CREATE TABLE "terraform_module" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "gitPath" TEXT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "description" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "terraform_module_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "terraform_module_organizationId_key" ON "terraform_module"("organizationId");

-- AddForeignKey
ALTER TABLE "git_repo" ADD CONSTRAINT "git_repo_terraformModuleId_fkey" FOREIGN KEY ("terraformModuleId") REFERENCES "terraform_module"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "terraform_module" ADD CONSTRAINT "terraform_module_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
