/*
  Warnings:

  - Added the required column `workspaceId` to the `aws_resource` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "aws_resource" ADD COLUMN     "workspaceId" INTEGER NOT NULL;

-- CreateTable
CREATE TABLE "workspace" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "state_backend" TEXT NOT NULL,
    "description" TEXT,

    CONSTRAINT "workspace_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "aws_resource" ADD CONSTRAINT "aws_resource_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "workspace"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workspace" ADD CONSTRAINT "workspace_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
