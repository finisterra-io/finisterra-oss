-- AlterTable
ALTER TABLE "aws_account" ALTER COLUMN "roleArn" DROP NOT NULL,
ALTER COLUMN "sessionDuration" SET DEFAULT 3600;
