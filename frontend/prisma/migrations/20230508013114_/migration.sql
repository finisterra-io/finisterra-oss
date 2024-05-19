/*
  Warnings:

  - A unique constraint covering the columns `[email]` on the table `invitation` will be added. If there are existing duplicate values, this will fail.

*/
-- AlterTable
ALTER TABLE "invitation" ADD COLUMN     "role" "userrole" NOT NULL DEFAULT 'MEMBER';

-- CreateIndex
CREATE UNIQUE INDEX "invitation_email_key" ON "invitation"("email");
