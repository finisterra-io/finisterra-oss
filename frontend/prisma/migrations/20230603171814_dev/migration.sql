/*
  Warnings:

  - The values [INITIAL_SCAN,DRIFT_FIXED] on the enum `RunTrigger` will be removed. If these variants are still used in the database, this will fail.

*/
-- AlterEnum
BEGIN;
CREATE TYPE "RunTrigger_new" AS ENUM ('MANUAL', 'SCHEDULED', 'PR_OPENED');
ALTER TABLE "run" ALTER COLUMN "trigger" TYPE "RunTrigger_new" USING ("trigger"::text::"RunTrigger_new");
ALTER TYPE "RunTrigger" RENAME TO "RunTrigger_old";
ALTER TYPE "RunTrigger_new" RENAME TO "RunTrigger";
DROP TYPE "RunTrigger_old";
COMMIT;
