import git from "simple-git";
import path from "path";
import { tmpdir } from "os";
import fs from "fs-extra";
import { createAppAuth } from "@octokit/auth-app";
import { Octokit } from "@octokit/rest";
import jwt from "jsonwebtoken";

export const generateJwt = () => {
  const payload = {
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 10 * 60,
    iss: process.env.GITHUB_APP_ID,
  };

  const token = jwt.sign(payload, process.env.GITHUB_APP_PEM, {
    algorithm: "RS256",
  });

  return token;
};

export const cloneGitRepo = async (account, gitRepo, branch) => {
  const app = createAppAuth({
    appId: process.env.GITHUB_APP_ID,
    privateKey: process.env.GITHUB_APP_PEM,
    installationId: account.installationId,
  });

  const installationAccessToken = await app({ type: "installation" });

  const jwt = generateJwt();
  const octokitWithJwt = new Octokit({
    auth: jwt,
  });

  const installation = await octokitWithJwt.apps.getInstallation({
    installation_id: account.installationId,
  });

  const organization = installation.data.account.login;

  const cloneUrl = `https://x-access-token:${installationAccessToken.token}@github.com/${organization}/${gitRepo.name}.git`;
  const clonePath = path.join(tmpdir(), "your-app-name", "temp", gitRepo.name);

  if (fs.existsSync(clonePath)) {
    fs.removeSync(clonePath);
  }

  await git().clone(cloneUrl, clonePath);

  const repo = git(clonePath);

  // Fetch all remote branches.
  await repo.fetch();

  // Check if the desired branch exists in the remote repository.
  const branchExists = await repo.branch(["--list", branch]);

  if (!branchExists.all.length) {
    // If the branch does not exist, create it based on the current HEAD.
    await repo.checkout(["-b", branch]);
    // Add a dummy empty commit.
    await repo.commit("Initial empty commit", { "--allow-empty": true });

    // Push the newly created branch to the remote repository.
    await repo.push("origin", branch);
  } else {
    // If it exists, just check it out.
    await repo.checkout(branch);
  }

  return { clonePath, installationAccessToken, installation };
};
