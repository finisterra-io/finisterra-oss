import { PrismaClient } from "@prisma/client";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";
import { Octokit } from "@octokit/rest";
import { getGithubCreds } from "utils/github/getGithubCreds";

const prisma = new PrismaClient();

async function listRepoPullRequests(octokit, owner, repo) {
  try {
    const { data } = await octokit.pulls.list({
      owner: owner,
      repo: repo,
      state: "open", // fetch open pull requests; change to "closed" for closed ones or "all" for both
    });

    return data;
  } catch (err) {
    console.error("Error fetching the pull requests:", err);
    throw err;
  }
}

export default async (req, res) => {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    return res.status(401).json({ message: "Unauthorized" });
  }

  if (req.method === "GET") {
    const gitRepoName = req.query.gitRepoName;
    const organizationId = session.organizationId;

    if (!gitRepoName) {
      return res.status(400).json({ error: "Required parameter missing." });
    }

    try {
      const account = await prisma.githubAccount.findUnique({
        where: { organizationId: parseInt(organizationId) },
      });

      if (!account || !account.installationId) {
        return res.status(500).json({ message: "Installation ID not found." });
      }

      const { installationAccessToken, installation } = await getGithubCreds(
        account
      );

      const octokit = new Octokit({ auth: installationAccessToken.token });
      const organization = installation.data.account.login;

      const pullRequests = await listRepoPullRequests(
        octokit,
        organization,
        gitRepoName
      );

      if (!pullRequests.length) {
        return res.status(200).json({ message: "No pull requests found." });
      }

      res.status(200).json({
        pullRequests: pullRequests.map((pr) => ({
          number: pr.number,
          title: pr.title,
          url: pr.html_url,
          created_at: pr.created_at,
          updated_at: pr.updated_at,
          user: {
            login: pr.user.login,
            avatar_url: pr.user.avatar_url,
            url: pr.user.html_url,
          },
          state: pr.state, // "open" or "closed"
        })),
      });
    } catch (error) {
      console.error(error);
      res.status(500).json({
        error: "An error occurred while fetching the pull requests.",
      });
    }
  } else {
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
