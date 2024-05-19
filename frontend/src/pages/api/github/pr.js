const { PrismaClient } = require("@prisma/client");
import { Octokit } from "@octokit/rest";
import { createAppAuth } from "@octokit/auth-app";

const prisma = new PrismaClient();

export default async (req, res) => {
  const authHeader = req.headers["authorization"];
  const apiKey = authHeader && authHeader.split(" ")[1];

  const validKey = await prisma.apiKey.findUnique({
    where: { key: apiKey },
  });

  if (!validKey) {
    res.status(401).json({ error: "Invalid API Key" });
    return;
  }

  if (req.method === "POST") {
    const { repositoryName, branchName, owner, pr_body } = req.body;

    if (!repositoryName || !branchName || !owner) {
      res
        .status(400)
        .json({ error: "Repository name, branch name, or owner missing" });
      return;
    }

    try {
      const organizationId = validKey.organizationId;
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

      // Check if a PR with the same head branch already exists
      const existingPRs = await octokitWithAuth.rest.pulls.list({
        owner: owner,
        repo: repositoryName.split("/")[1],
        head: owner + ":" + branchName,
      });

      if (existingPRs.data.length > 0) {
        res.status(200).json({ message: "Pull request already exists." });
        return;
      }

      const pr = await octokitWithAuth.rest.pulls.create({
        owner: owner,
        repo: repositoryName.split("/")[1],
        title: `Finisterra code ${branchName}`,
        head: branchName,
        base: "main",
        body: pr_body,
      });

      res.status(200).json({ url: pr.data.html_url });
    } catch (error) {
      console.error(error);
      res.status(500).json({
        error: "An error occurred while creating the pull request.",
      });
    }
  } else {
    res.setHeader("Allow", ["POST"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
