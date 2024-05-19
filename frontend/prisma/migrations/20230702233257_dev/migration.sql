-- AddForeignKey
ALTER TABLE "terraform_module_instance" ADD CONSTRAINT "terraform_module_instance_TerraformModuleId_fkey" FOREIGN KEY ("TerraformModuleId") REFERENCES "terraform_module"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
