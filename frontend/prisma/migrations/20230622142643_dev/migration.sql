-- AlterTable
ALTER TABLE "aws_account" ADD COLUMN     "AccessKeyId" TEXT,
ADD COLUMN     "SecretAccessKey" TEXT,
ADD COLUMN     "SessionToken" TEXT;
