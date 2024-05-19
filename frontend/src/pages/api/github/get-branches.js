const { PrismaClient } = require("@prisma/client");
import { Octokit } from "@octokit/rest";
import { createAppAuth } from "@octokit/auth-app";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

const prisma = new PrismaClient();

export default async (req, res) => {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  if (req.method === "GET") {
    const organizationId = session.organizationId;
    const { repoName, owner } = req.query;

    try {
      const account = await prisma.githubAccount.findUnique({
        where: { organizationId: parseInt(organizationId) },
      });

      if (!account || !account.installationId) {
        res.status(500).json({ error: "Installation ID not found." });
        return;
      }

      const app = createAppAuth({
        appId: process.env.GITHUB_APP_ID,
        privateKey: process.env.GITHUB_APP_PEM,
        installationId: account.installationId,
      });

      const installationAccessToken = await app({ type: "installation" });

      const octokitWithAuth = new Octokit({
        auth: installationAccessToken.token,
      });

      // Fetch all branches
      const branches = await octokitWithAuth.paginate(
        octokitWithAuth.rest.repos.listBranches,
        {
          owner,
          repo: repoName,
          per_page: 100,
        }
      );

      res.status(200).json(branches);
    } catch (error) {
      console.error(error);
      res
        .status(500)
        .json({ error: "An error occurred while fetching the branches." });
    }
  } else {
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
