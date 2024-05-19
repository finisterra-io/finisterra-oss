const { PrismaClient } = require("@prisma/client");
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

const prisma = new PrismaClient();

export default async function handle(req, res) {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  if (req.method !== "POST") {
    return res.status(405).json({ message: "Method not allowed" });
  }
  const organizationId = session.organizationId;

  const { branch, githubAccountId, gitRepoId, path, awsAccountId } = req.body;

  try {
    // Start a transaction
    const newGitRepo = await prisma.$transaction([
      prisma.gitRepo.upsert({
        where: {
          gitrepoId_organizationId: {
            gitrepoId: gitRepoId,
            organizationId: organizationId,
          },
        },
        update: {
          githubAccountId: githubAccountId,
        },
        create: {
          gitrepoId: gitRepoId,
          githubAccountId: githubAccountId,
          organizationId: organizationId,
        },
      }),
      prisma.awsAccountGitRepo.upsert({
        where: {
          awsAccountId_gitRepoId_organizationId: {
            awsAccountId: awsAccountId,
            gitRepoId: gitRepoId,
            organizationId: organizationId,
          },
        },
        update: {
          branch: branch,
          path: path,
        },
        create: {
          awsAccountId: awsAccountId,
          branch: branch,
          path: path,
          organizationId: organizationId,
          gitRepo: {
            connect: {
              id: gitRepoId,
            },
          },
        },
      }),
    ]);

    return res.status(200).json(newGitRepo);
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      message:
        "Error occurred while creating or updating the GitRepo and AwsAccountGitRepo",
    });
  }
}
