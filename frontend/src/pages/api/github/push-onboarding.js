import { PrismaClient } from "@prisma/client";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";
import path from "path";
import fs from "fs-extra";
import git from "simple-git";
import { Octokit } from "@octokit/rest";
import { cloneGitRepo } from "utils/github/cloneGitRepo";
import sodium from "sodium-native";

const prisma = new PrismaClient();

import util from "util";

const copyFile = util.promisify(fs.copyFile);

async function copyWorkflowFiles(clonePath, awsAccountId, awsRegion) {
  const workflowDir = path.join(clonePath, ".github", "workflows");
  fs.ensureDirSync(workflowDir);
  const awsDir = path.join(clonePath, "finisterra", "generated", "aws");
  fs.ensureDirSync(awsDir);
  const regionDir = path.join(
    clonePath,
    "finisterra",
    "generated",
    "aws",
    awsAccountId,
    awsRegion
  );
  fs.ensureDirSync(regionDir);

  const onboardFiles = [
    "apply_terragrunt.yaml",
    "generate_tf_code.yaml",
    "plan_terragrunt.yaml",
    ".gitignore",
    "terragrunt.hcl",
  ];
  const absolutePathToOnboard = path.join(
    process.cwd(),
    "public",
    "onboarding"
  );
  await Promise.all(
    onboardFiles.map(async (file) => {
      let targetFile = file;
      if (file === "generate_tf_code.yaml") {
        targetFile = `generate_tf_code_${awsAccountId}_${awsRegion}.yaml`;
      }
      let targetDir;
      if (
        file == "apply_terragrunt.yaml" ||
        file == "plan_terragrunt.yaml" ||
        file == "generate_tf_code.yaml"
      ) {
        targetDir = workflowDir;
      } else if (file == ".gitignore") {
        targetDir = awsDir;
      } else if (file == "terragrunt.hcl") {
        targetDir = regionDir;
      }

      await copyFile(
        path.join(absolutePathToOnboard, file),
        path.join(targetDir, targetFile)
      );

      let fileContent = await fs.readFile(
        path.join(targetDir, targetFile),
        "utf8"
      );
      fileContent = fileContent.replace(/<AWS_ACCOUNT_ID>/g, awsAccountId);
      fileContent = fileContent.replace(/<AWS_REGION>/g, awsRegion);
      fileContent = fileContent.replace(
        /<FT_API_HOST>/g,
        process.env.FT_API_HOST
      );
      await fs.writeFile(path.join(targetDir, targetFile), fileContent, "utf8");
    })
  );
}

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

  if (req.method === "POST") {
    const { gitRepo, ftAPIKey, awsAccountId, awsRegion } = req.body;

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

      const { data: publicKey } = await octokit.actions.getRepoPublicKey({
        owner: organization,
        repo: gitRepo.name,
      });

      const message = Buffer.from(ftAPIKey.key);
      const publicKeyBuffer = Buffer.from(publicKey.key, "base64");
      const encryptedValue = Buffer.alloc(
        sodium.crypto_box_SEALBYTES + message.length
      );

      sodium.crypto_box_seal(encryptedValue, message, publicKeyBuffer);

      await octokit.actions.createOrUpdateRepoSecret({
        owner: organization,
        repo: gitRepo.name,
        secret_name: "FT_API_KEY",
        encrypted_value: encryptedValue.toString("base64"),
        key_id: publicKey.key_id,
      });

      const repo = git(clonePath);

      await repo.checkout("main");

      const remote = `https://x-access-token:${installationAccessToken.token}@github.com/${organization}/${gitRepo.name}.git`;
      await repo.pull(remote, "main");

      const newBranch = `finisterra-initial-setup-${awsAccountId}-${awsRegion}`;
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

      await copyWorkflowFiles(clonePath, awsAccountId, awsRegion);
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

      await repo.commit(
        `Add finisterra-initial-setup-${awsAccountId}-${awsRegion}`
      );
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
          title: `Finisterra Initial Setup For ${awsAccountId} ${awsRegion}`,
          head: newBranch,
          base: "main",
          body: "Dummy description",
        });
        pull = result.data;
      }

      pull.merged = false;
      pull.message = "PR Created successfully.";
      res.status(200).json(pull);

      try {
        // Attempting to merge the created pull request
        await octokit.pulls.merge({
          owner: organization,
          repo: gitRepo.name,
          pull_number: pull.number,
        });
        pull.merged = true;
        pull.message = "PR Created and merged successfully.";
        res.status(200).json(pull);
      } catch (mergeError) {
        console.error("Error while merging PR:", mergeError);
        pull.message = "PR Created but not merged.";
        res.status(200).json(pull);
      }
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
