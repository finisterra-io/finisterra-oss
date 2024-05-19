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

async function getLatestWorkflowRun(
  octokit,
  owner,
  repo,
  workflowId,
  head_branch
) {
  try {
    const { data } = await octokit.actions.listWorkflowRuns({
      owner: owner,
      repo: repo,
      workflow_id: workflowId,
      per_page: 50, // Increased per_page for better filtering, adjust as needed
    });

    // Filter the runs by the head_branch
    const runsWithMatchingBranch = data.workflow_runs.filter(
      (run) => run.head_branch === head_branch
    );

    // Sort the runs by their created_at timestamp in descending order
    // So that the newest one will be at the beginning of the array
    runsWithMatchingBranch.sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );

    // Return the newest run if it exists
    return runsWithMatchingBranch[0];
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

  if (req.method === "GET") {
    const gitRepoName = req.query.gitRepoName;
    const workflow = req.query.workflow;
    const organizationId = session.organizationId;
    const head_branch = req.query.head_branch;

    if (!gitRepoName || !workflow || !head_branch) {
      return res.status(400).json({ error: "Required parameters missing." });
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

      const { data: publicKey } = await octokit.actions.getRepoPublicKey({
        owner: organization,
        repo: gitRepoName,
      });

      const latestRun = await getLatestWorkflowRun(
        octokit,
        organization,
        gitRepoName,
        workflow,
        head_branch
      );

      if (!latestRun) {
        return res.status(200).json({ message: "Workflow run not found." });
      }

      const status = latestRun.status; // status: "queued", "in_progress", "completed"
      const conclusion = latestRun.conclusion; // conclusion: "success", "failure", "cancelled" (only if status is "completed")
      const workflowUrl = latestRun.html_url; // the URL for the workflow run

      res.status(200).json({
        status: status,
        conclusion: conclusion,
        workflowUrl: workflowUrl, // Added this line to send the URL
      });
    } catch (error) {
      console.error(error);
      res.status(500).json({
        error: "An error occurred while fetching the workflow status.",
      });
    }
  } else {
    res.setHeader("Allow", ["POST"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
