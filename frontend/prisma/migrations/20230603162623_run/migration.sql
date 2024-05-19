-- CreateEnum
CREATE TYPE "RunStatus" AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "RunTrigger" AS ENUM ('MANUAL', 'SCHEDULED', 'INITIAL_SCAN', 'DRIFT_FIXED');

-- CreateTable
CREATE TABLE "run" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "status" "RunStatus" NOT NULL,
    "trigger" "RunTrigger" NOT NULL,
    "logFile" TEXT NOT NULL,
    "workspaceId" INTEGER NOT NULL,

    CONSTRAINT "run_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "run" ADD CONSTRAINT "run_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "run" ADD CONSTRAINT "run_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "workspace"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
