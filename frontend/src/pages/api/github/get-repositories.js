const { PrismaClient } = require("@prisma/client");
import { Octokit } from "@octokit/rest";
import { createAppAuth } from "@octokit/auth-app";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

const prisma = new PrismaClient();

export default async (req, res) => {
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
      // Retrieve the installation ID from the GithubAccount table
      const account = await prisma.githubAccount.findUnique({
        where: { organizationId: parseInt(organizationId) },
      });

      if (!account || !account.installationId) {
        res.status(500).json({ error: "Installation ID not found." });
        return;
      }

      // Generate an installation access token
      const app = createAppAuth({
        appId: process.env.GITHUB_APP_ID,
        privateKey: process.env.GITHUB_APP_PEM,
        installationId: account.installationId,
      });

      const installationAccessToken = await app({ type: "installation" });

      // Instantiate a new Octokit with the installation access token
      const octokitWithAuth = new Octokit({
        auth: installationAccessToken.token,
      });

      // Prepare to paginate
      let fetchMore = true;
      let page = 1; // page numbering starts at 1
      const per_page = 100; // you can adjust per_page to another number, keeping in mind the rate limits
      const allRepositories = [];

      while (fetchMore) {
        // Fetch a page of repositories
        const response =
          await octokitWithAuth.rest.apps.listReposAccessibleToInstallation({
            per_page,
            page,
          });

        // Add the repositories from this response to our full list
        allRepositories.push(...response.data.repositories);

        // Prepare the next page if it exists, otherwise end the loop
        if (
          response.data.repositories.length < per_page ||
          !response.data.repositories.length
        ) {
          // If we retrieved fewer items than requested, it's the last page
          fetchMore = false;
        } else {
          // Otherwise, increase the page index to get the next page
          page++;
        }
      }

      // Return the full list of repositories
      res.status(200).json({
        repositories: allRepositories,
        installationId: account.installationId,
        organization: allRepositories[0].owner.login,
      });
      res.status(200).json(allRepositories);
    } catch (error) {
      console.error(error);
      res
        .status(500)
        .json({ error: "An error occurred while fetching the repositories." });
    }
  } else {
    // Handle any other HTTP method
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
