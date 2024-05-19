-- CreateTable
CREATE TABLE "aws_account_provider_group" (
    "awsAccountId" INTEGER NOT NULL,
    "providerGroupId" INTEGER NOT NULL,
    "organizationId" INTEGER NOT NULL,

    CONSTRAINT "aws_account_provider_group_pkey" PRIMARY KEY ("awsAccountId","providerGroupId")
);

-- AddForeignKey
ALTER TABLE "aws_account_provider_group" ADD CONSTRAINT "aws_account_provider_group_awsAccountId_fkey" FOREIGN KEY ("awsAccountId") REFERENCES "aws_account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "aws_account_provider_group" ADD CONSTRAINT "aws_account_provider_group_providerGroupId_fkey" FOREIGN KEY ("providerGroupId") REFERENCES "provider_group"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "aws_account_provider_group" ADD CONSTRAINT "aws_account_provider_group_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
