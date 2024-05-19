-- CreateTable
CREATE TABLE "github_user" (
    "id" SERIAL NOT NULL,
    "login" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "github_user_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "github_organization" (
    "id" SERIAL NOT NULL,
    "login" TEXT NOT NULL,
    "githubUserId" INTEGER,
    "installationId" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "github_organization_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "github_user_login_key" ON "github_user"("login");

-- CreateIndex
CREATE UNIQUE INDEX "github_organization_login_key" ON "github_organization"("login");

-- CreateIndex
CREATE UNIQUE INDEX "github_organization_installationId_key" ON "github_organization"("installationId");

-- AddForeignKey
ALTER TABLE "github_organization" ADD CONSTRAINT "github_organization_githubUserId_fkey" FOREIGN KEY ("githubUserId") REFERENCES "github_user"("id") ON DELETE SET NULL ON UPDATE CASCADE;
