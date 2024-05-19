import { PrismaClient } from "@prisma/client";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";
import { Octokit } from "@octokit/rest";
import { getGithubCreds } from "utils/github/getGithubCreds";

const prisma = new PrismaClient();

async function triggerWorkflowDispatch(
  octokit,
  owner,
  repo,
  workflowId,
  branch
) {
  try {
    await octokit.actions.createWorkflowDispatch({
      owner: owner,
      repo: repo,
      workflow_id: workflowId,
      ref: branch,
    });
    console.log("Workflow triggered successfully.");
  } catch (err) {
    console.error("Error triggering the workflow:", err);
    throw err;
  }
}

async function doesBranchExist(octokit, owner, repo, branch) {
  try {
    await octokit.repos.getBranch({
      owner: owner,
      repo: repo,
      branch: branch,
    });
    return true;
  } catch (err) {
    return false;
  }
}

async function getLatestWorkflowRun(octokit, owner, repo, workflowId) {
  try {
    const { data } = await octokit.actions.listWorkflowRuns({
      owner: owner,
      repo: repo,
      workflow_id: workflowId,
      per_page: 1,
    });

    // Return the most recent run if it exists
    return data.workflow_runs[0];
  } catch (err) {
    console.error("Error fetching the workflow run:", err);
    throw err;
  }
}

export default async (req, res) => {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    return res.status(401).json({ message: "Unauthorized" });
  }

  if (req.method === "POST") {
    const { gitRepo, workflow, ref } = req.body;
    const organizationId = session.organizationId;

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

      const { data: publicKey } = await octokit.actions.getRepoPublicKey({
        owner: organization,
        repo: gitRepo.name,
      });

      const branchExists = await doesBranchExist(
        octokit,
        organization,
        gitRepo.name,
        ref
      );
      const targetBranch = branchExists ? ref : "main";

      await triggerWorkflowDispatch(
        octokit,
        organization,
        gitRepo.name,
        workflow,
        targetBranch
      );

      const latestRun = await getLatestWorkflowRun(
        octokit,
        organization,
        gitRepo.name,
        workflow
      );
      res.status(200).json(latestRun);
    } catch (error) {
      console.error(error);
      res
        .status(500)
        .json({ error: "An error occurred while processing the request." });
    }
  } else {
    res.setHeader("Allow", ["POST"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
