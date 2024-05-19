/*
  Warnings:

  - Added the required column `workspaceId` to the `terraform_module_instance` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "terraform_module_instance" ADD COLUMN     "workspaceId" INTEGER NOT NULL;

-- AddForeignKey
ALTER TABLE "terraform_module_instance" ADD CONSTRAINT "terraform_module_instance_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "workspace"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
