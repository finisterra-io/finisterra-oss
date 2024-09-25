import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";
import { updateSubscription } from "utils/billing/subscription";

import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export default async function handler(req, res) {
  const { method, body, query } = req;
  
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
  
  if (!organizationId) {
    res.status(400).json({ message: "Missing organizationId in the session" });
    return;
  }
  
  switch (method) {
    case "GET":
    try {
      let accounts = await prisma.awsAccount.findMany({
        where: { organizationId },
        include: {
          tags: true,
          awsAccountGitRepos: {
            include: {
              gitRepo: true,
            },
          },
          Workspace: {
            include: {
              providerGroup: true,
            },
          },
        },
      });
      
      // After fetching, reshape the data as you do in the POST/PUT methods.
      accounts = accounts.map((account) => {
        const awsAccountGitRepo = account.awsAccountGitRepos[0]; // Assuming only one repo per account
        const githubData = awsAccountGitRepo
        ? {
          ...awsAccountGitRepo.gitRepo,
          branch: { name: awsAccountGitRepo.branch },
          path: awsAccountGitRepo.path,
          name: {
            name: awsAccountGitRepo.gitRepo.name,
            id: awsAccountGitRepo.gitRepo.id,
          },
        }
        : null; // Default to null if no GitRepo associated
        
        const workspace = {
          awsRegion: account.Workspace[0]
          ? { name: account.Workspace[0].awsRegion }
          : null,
          activeGroups: account.Workspace.map(
            (groupRel) => groupRel.providerGroup
          ),
        };
        
        return {
          ...account,
          githubData,
          workspace: workspace,
        };
      });
      
      res.status(200).json({ accounts });
    } catch (error) {
      console.log(error);
      
      res.status(500).json({ message: "Error fetching accounts" });
    } finally {
      await prisma.$disconnect();
    }
    break;
    
    case "POST":
    case "PUT":
    try {
      const { id, githubData, workspace, awsRegion, ...accountData } = body;
      
      //count enabled = true in awsAccount
      const enabledAwsAccountsCount = await prisma.awsAccount.count({
        where: {
          organizationId: organizationId,
          enabled: true,
          region: {
            not: "global",
          },
        },
      });
      
      const organization = await prisma.organization.findUnique({
        where: { id: organizationId },
      });
      
      let activeSubscription;
      if (organization && organization.subscriptionActive) {
        activeSubscription = true;
      } else {
        activeSubscription = false;
      }
      
      if (enabledAwsAccountsCount >= 1 && id == null) {
        if (!activeSubscription) {
          return res
          .status(404)
          .json({ error: "No Active subscription not found" });
        }
      }
      
      var account = null;
      if (id) {
        if (accountData.organizationId == null) {
          accountData.organizationId = organizationId;
        }
        account = await prisma.awsAccount.upsert({
          where: { id },
          create: {
            ...accountData,
            tags: {
              create: accountData.tags,
            },
          },
          update: {
            ...accountData,
            tags: {
              upsert: accountData.tags.map((tag) => ({
                where: { id: tag.id },
                update: tag,
                create: tag,
              })),
            },
          },
          include: { tags: true },
        });
      } else {
        console.log(accountData);
        account = await prisma.awsAccount.create({
          data: {
            ...accountData,
            organization: {
              connect: { id: organizationId },
            },
            tags: {
              create: accountData.tags,
            },
            region: accountData.region,
          },
          include: { tags: true },
        });
      }
      
      // Update the subscription
      updateSubscription({ organizationId });
      
      if (githubData) {
        //Add gitRepo to the account
        const { branch, githubAccountId, name, path } = githubData;
        const gitRepo = name;
        const awsAccountId = parseInt(account.awsAccountId);
        
        const newGitRepo = await prisma.gitRepo.upsert({
          where: {
            gitrepoId_organizationId: {
              gitrepoId: gitRepo.id,
              organizationId: organizationId,
            },
          },
          update: {
            githubAccountId: githubAccountId,
            name: gitRepo.name,
          },
          create: {
            gitrepoId: gitRepo.id,
            name: gitRepo.name,
            githubAccountId: githubAccountId,
            organizationId: organizationId,
            githubAccount: {
              connect: {
                organizationId: organizationId,
              },
            },
          },
        });
        
        const newAwsAccountGitRepo = await prisma.awsAccountGitRepo.upsert({
          where: {
            awsAccountId_gitRepoId_organizationId: {
              awsAccountId: account.id,
              gitRepoId: gitRepo.id,
              organizationId: organizationId,
            },
          },
          update: {
            branch: branch.name,
            path: path,
          },
          create: {
            branch: branch,
            path: path,
            organizationId: organizationId,
            gitRepo: {
              connect: {
                id: newGitRepo.id,
              },
            },
            awsAccount: {
              connect: {
                id: account.id,
              },
            },
          },
        });
        
        account.githubData = githubData;
      }
      
      if (awsRegion) {
        // Get the list of groups
        const providerGroups = await prisma.provider.findUnique({
          where: { name: "AWS" }, // use providerName in the where clause
          include: {
            ProviderGroup: {
              where: { active: true },
            },
          },
        });
        
        await Promise.all(
          providerGroups.ProviderGroup.map((group) => {
            let region = awsRegion.code;
            
            if (group.code === "iam") {
              region = "global";
            }
            
            const workspaceName =
            account.awsAccountId + "-" + region + "-" + group.code;
            return prisma.workspace.upsert({
              where: {
                // Define the unique identifier for the record
                awsAccountId_providerGroupId_awsRegion_organizationId: {
                  awsAccountId: account.id,
                  providerGroupId: group.id,
                  awsRegion: region,
                  organizationId: organizationId,
                },
              },
              update: {
                // Fields to update when the record exists
                name: workspaceName,
                scanInterval: 86400,
              },
              create: {
                // Fields to create when the record doesn't exist
                name: workspaceName,
                scanInterval: 86400,
                awsAccount: {
                  connect: {
                    id: account.id,
                  },
                },
                providerGroup: {
                  connect: {
                    id: group.id,
                  },
                },
                organization: {
                  connect: {
                    id: organizationId,
                  },
                },
                awsRegion: region,
              },
            });
          })
        );
      }
      
      res.status(200).json({ account });
    } catch (error) {
      console.log(error);
      if (error.code === 'P2002' && error.meta?.target?.includes('awsAccountId') && error.meta?.target?.includes('region')) {
        res.status(400).json({ error: 'An account with this AWS Account ID and Region already exists.' });
      } else {
        res.status(500).json({ message: "Error creating account" });
      }
    } finally {
      await prisma.$disconnect();
    }
    break;
    
    case "DELETE":
    try {
      const id = parseInt(query.id, 10); // Convert the id to an integer
      
      // Find the account with the specified id and organizationId
      const account = await prisma.awsAccount.findFirst({
        where: { id, organizationId },
      });
      
      if (account) {
        // Delete the account using its id
        await prisma.awsAccount.delete({
          where: { id: account.id, organizationId },
        });
        res.status(200).json({ message: "Account deleted successfully" });
      } else {
        res.status(404).json({ message: "Account not found" });
      }
    } catch (error) {
      console.log(error);
      res.status(500).json({ message: "Error deleting account" });
    } finally {
      await prisma.$disconnect();
    }
    break;
    
    default:
    res.setHeader("Allow", ["GET", "POST", "PUT", "DELETE"]);
    res.status(405).end(`Method ${method} Not Allowed`);
  }
}
