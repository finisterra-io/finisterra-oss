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

export const getGithubCreds = async (account) => {
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

  return { installationAccessToken, installation };
};
