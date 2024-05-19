import { PrismaClient } from "@prisma/client";
import { Octokit } from "@octokit/rest";
import { createAppAuth } from "@octokit/auth-app";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

const prisma = new PrismaClient();

export default async function handler(req, res) {
  const authHeader = req.headers["authorization"];
  const apiKey = authHeader && authHeader.split(" ")[1];

  let validKey;
  if (apiKey) {
    validKey = await prisma.apiKey.findUnique({
      where: { key: apiKey },
    });
  }

  const session = await getServerSession(req, res, authOptions);

  if (!session && !validKey) {
    res.status(401).json({ message: "Unauthorized" });
    return;
  }
  let organizationId;

  if (session) {
    organizationId = session.organizationId;
  } else {
    organizationId = validKey.organizationId;
  }

  if (req.method === "GET") {
    try {
      const githubAccount = await prisma.githubAccount.findFirst({
        where: { organizationId: organizationId },
      });

      if (!githubAccount) {
        res.status(404).json({ message: "GitHub account not found" });
        return;
      }

      // Generate an installation access token
      const app = createAppAuth({
        appId: process.env.GITHUB_APP_ID,
        privateKey: process.env.GITHUB_APP_PEM,
        installationId: githubAccount.installationId,
      });

      const installationAccessToken = await app({ type: "installation" });

      // Instantiate a new Octokit with the installation access token
      const octokitWithAuth = new Octokit({
        auth: installationAccessToken.token,
      });

      // Fetch the repositories
      const repos =
        await octokitWithAuth.rest.apps.listReposAccessibleToInstallation();

      if (repos.data.repositories && repos.data.repositories.length > 0) {
        res.status(200).json(repos.data.repositories);
      } else {
        res.status(404).json({
          message: "No repositories found for the GitHub App installation.",
        });
      }
    } catch (error) {
      console.error(error);
      res.status(500).json({ error: "Failed to check GitHub account" });
    }
  } else {
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
