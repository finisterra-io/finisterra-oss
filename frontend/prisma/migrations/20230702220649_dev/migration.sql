-- AddForeignKey
ALTER TABLE "terraform_module" ADD CONSTRAINT "terraform_module_providerGroupId_fkey" FOREIGN KEY ("providerGroupId") REFERENCES "provider_group"("id") ON DELETE SET NULL ON UPDATE CASCADE;
