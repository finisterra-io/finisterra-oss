/*
  Warnings:

  - You are about to drop the `AwsIntegration` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "AwsIntegration" DROP CONSTRAINT "AwsIntegration_organizationId_fkey";

-- DropTable
DROP TABLE "AwsIntegration";

-- CreateTable
CREATE TABLE "AwsAccount" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "roleArn" TEXT NOT NULL,
    "sessionDuration" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "AwsAccount_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "AwsAccount" ADD CONSTRAINT "AwsAccount_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
