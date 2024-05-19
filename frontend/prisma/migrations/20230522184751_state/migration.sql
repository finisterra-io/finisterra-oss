-- CreateTable
CREATE TABLE "aws_state_config" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "awsAccountId" INTEGER NOT NULL,
    "awsRegion" TEXT NOT NULL,
    "s3Bucket" TEXT NOT NULL,
    "dynamoDbTable" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "aws_state_config_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "aws_state_config" ADD CONSTRAINT "aws_state_config_awsAccountId_fkey" FOREIGN KEY ("awsAccountId") REFERENCES "aws_account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
