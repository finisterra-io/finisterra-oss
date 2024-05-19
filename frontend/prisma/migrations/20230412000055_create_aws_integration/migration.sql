/*
  Warnings:

  - You are about to drop the `AwsAccount` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `AwsAccountTag` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Tag` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "AwsAccount" DROP CONSTRAINT "AwsAccount_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "AwsAccountTag" DROP CONSTRAINT "AwsAccountTag_awsAccountId_fkey";

-- DropForeignKey
ALTER TABLE "AwsAccountTag" DROP CONSTRAINT "AwsAccountTag_tagId_fkey";

-- DropTable
DROP TABLE "AwsAccount";

-- DropTable
DROP TABLE "AwsAccountTag";

-- DropTable
DROP TABLE "Tag";

-- CreateTable
CREATE TABLE "aws_account" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "roleArn" TEXT NOT NULL,
    "sessionDuration" INTEGER NOT NULL,
    "description" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "aws_account_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tag" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,

    CONSTRAINT "tag_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "aws_account_tag" (
    "awsAccountId" INTEGER NOT NULL,
    "tagId" INTEGER NOT NULL,

    CONSTRAINT "aws_account_tag_pkey" PRIMARY KEY ("awsAccountId","tagId")
);

-- CreateIndex
CREATE UNIQUE INDEX "tag_name_key" ON "tag"("name");

-- AddForeignKey
ALTER TABLE "aws_account" ADD CONSTRAINT "aws_account_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "aws_account_tag" ADD CONSTRAINT "aws_account_tag_awsAccountId_fkey" FOREIGN KEY ("awsAccountId") REFERENCES "aws_account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "aws_account_tag" ADD CONSTRAINT "aws_account_tag_tagId_fkey" FOREIGN KEY ("tagId") REFERENCES "tag"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
