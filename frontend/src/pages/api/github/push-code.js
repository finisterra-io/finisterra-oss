import { PrismaClient } from "@prisma/client";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";
const path = require("path");
const fs = require("fs-extra");
const git = require("simple-git");
import { Octokit } from "@octokit/rest";
import { cloneGitRepo } from "utils/github/cloneGitRepo";
const formidable = require("formidable");
const prisma = new PrismaClient();
const AdmZip = require("adm-zip");

export const config = {
  api: {
    bodyParser: false,
  },
};

const extractZip = async (zipFilePath, destinationPath, remotePath) => {
  try {
    // Ensure the destination directory exists
    const fullPath = path.join(destinationPath, remotePath);
    await fs.ensureDir(fullPath);

    // Using adm-zip to extract the ZIP file
    const zip = new AdmZip(zipFilePath);

    // Extract each entry
    zip.extractAllTo(fullPath, true);

    return Promise.resolve();
  } catch (error) {
    console.error(`Extraction error: ${error}`);
    return Promise.reject(error);
  }
};

export default async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }
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

  const form = new formidable.IncomingForm();
  form.parse(req, async (err, fields, files) => {
    if (err) {
      console.error(err);
      return res.status(500).json({ error: "Error parsing form data" });
    }

    const { repositoryName, branchName, remotePath } = fields;
    const gitRepo = { name: repositoryName[0] };
    const newBranch = branchName[0];
    const newRemotePath = remotePath[0];
    const zipFile = files.zipFile[0];

    if (!gitRepo || !newBranch || !zipFile) {
      return res.status(400).json({ error: "Missing required fields" });
    }

    let tmpClonePath;

    try {
      const account = await prisma.githubAccount.findUnique({
        where: { organizationId: parseInt(organizationId) },
      });

      if (!account || !account.installationId) {
        return res.status(500).json({ message: "Installation ID not found." });
      }

      const { clonePath, installationAccessToken, installation } =
        await cloneGitRepo(account, gitRepo, "main");

      const octokit = new Octokit({ auth: installationAccessToken.token });
      const organization = installation.data.account.login;

      tmpClonePath = clonePath;

      const repo = git(clonePath);

      await repo.checkout("main");

      const remote = `https://x-access-token:${installationAccessToken.token}@github.com/${organization}/${gitRepo.name}.git`;
      await repo.pull(remote, "main");

      const listLocalBranches = async () => {
        const listSummary = await repo.branchLocal();
        return listSummary.all || [];
      };

      const localBranches = await listLocalBranches();
      const branchExistsLocally = localBranches.includes(newBranch);

      const remoteBranches = await repo.listRemote(["--heads"]);
      const branchExistsRemotely = remoteBranches.includes(
        `refs/heads/${newBranch}`
      );

      if (branchExistsLocally) {
        await repo.checkout(newBranch);
      } else if (branchExistsRemotely) {
        await repo.fetch();
        await repo.checkout(newBranch);
      } else {
        await repo.checkoutLocalBranch(newBranch);
      }

      // Check if there's already a pull request for the branch
      const { data: existingPulls } = await octokit.pulls.list({
        owner: organization,
        repo: gitRepo.name,
        head: `${organization}:${newBranch}`,
      });

      await extractZip(zipFile.filepath, clonePath, newRemotePath);

      await repo.add(".");

      // Check for changes
      const statusSummary = await repo.status();
      if (!statusSummary.files.length) {
        // If there's an existing PR, return it.
        if (existingPulls.length > 0) {
          const existingPull = existingPulls[0];
          existingPull.merged = false;
          existingPull.message =
            "No changes detected, but an existing pull request was found.";
          return res.status(200).json(existingPull);
        }

        // If no PR exists and no changes detected, return the standard message.
        return res.status(200).json({ message: "No changes detected" });
      }

      await repo.commit(`Add ${newBranch}`);
      await repo.push(remote, newBranch);

      // If there's an existing PR, use it instead of creating a new one.
      let pull;
      if (existingPulls.length > 0) {
        pull = existingPulls[0];
      } else {
        // Otherwise, create a new pull request.
        const result = await octokit.pulls.create({
          owner: organization,
          repo: gitRepo.name,
          title: `Finisterra code ${newBranch}`,
          head: newBranch,
          base: "main",
          body: `Finisterra code ${newBranch}\n[skip cicd]`,
        });
        pull = result.data;
      }

      pull.merged = false;
      pull.message = "PR Created successfully.";
      res.status(200).json(pull);
    } catch (error) {
      console.error(error);
      res
        .status(500)
        .json({ error: "An error occurred while processing the request." });
    } finally {
      await fs.remove(tmpClonePath);
    }
  });
};
