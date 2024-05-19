-- CreateEnum
CREATE TYPE "ScanStatus" AS ENUM ('STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "ScanTrigger" AS ENUM ('MANUAL', 'SCHEDULED', 'INITIAL_SCAN');

-- CreateTable
CREATE TABLE "scan" (
    "id" SERIAL NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "status" "ScanStatus" NOT NULL,
    "trigger" "ScanTrigger" NOT NULL,
    "logFile" TEXT NOT NULL,
    "workspaceId" INTEGER NOT NULL,

    CONSTRAINT "scan_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "scan" ADD CONSTRAINT "scan_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "workspace"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
