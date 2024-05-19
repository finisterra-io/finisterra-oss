-- CreateTable
CREATE TABLE "github_account" (
    "id" SERIAL NOT NULL,
    "organizationId" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "installationId" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "github_account_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "git_repo" (
    "id" SERIAL NOT NULL,
    "githubAccountId" INTEGER NOT NULL,
    "path" TEXT NOT NULL,
    "branch" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "git_repo_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "aws_account_git_repo" (
    "id" SERIAL NOT NULL,
    "awsAccountId" INTEGER NOT NULL,
    "gitRepoId" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "aws_account_git_repo_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "github_account" ADD CONSTRAINT "github_account_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "organization"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "git_repo" ADD CONSTRAINT "git_repo_githubAccountId_fkey" FOREIGN KEY ("githubAccountId") REFERENCES "github_account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "aws_account_git_repo" ADD CONSTRAINT "aws_account_git_repo_awsAccountId_fkey" FOREIGN KEY ("awsAccountId") REFERENCES "aws_account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "aws_account_git_repo" ADD CONSTRAINT "aws_account_git_repo_gitRepoId_fkey" FOREIGN KEY ("gitRepoId") REFERENCES "git_repo"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
