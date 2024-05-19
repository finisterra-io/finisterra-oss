/*
  Warnings:

  - You are about to drop the column `dynamoDbTable` on the `aws_state_config` table. All the data in the column will be lost.
  - Added the required column `dynamoDBTable` to the `aws_state_config` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "aws_state_config" DROP COLUMN "dynamoDbTable",
ADD COLUMN     "dynamoDBTable" TEXT NOT NULL;
