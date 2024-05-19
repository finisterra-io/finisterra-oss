import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

export default async function handle(req, res) {
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

  const { id } = req.query; // Extracting id from the query

  // Receive optional awsAccountId
  const awsAccountId = req.query.awsAccountId
    ? Number(req.query.awsAccountId)
    : null;

  switch (req.method) {
    case "GET":
      try {
        if (session) {
          const workspaces = await prisma.workspace.findMany({
            where: {
              organizationId: Number(organizationId),
              awsAccountId: awsAccountId || undefined,
            },
            select: {
              id: true,
              name: true,
              organizationId: true,
              awsAccountId: true,
              providerGroupId: true,
              awsRegion: true,
              description: true,
              createdAt: true,
              updatedAt: true,
              awsAccount: true,
              providerGroup: true,
              organization: true,
              enabled: true,
            },
          });

          return res.status(200).json({ workspaces });
        } else {
          const awsAccountId = req.query.awsAccountId;
          const awsRegion = req.query.awsRegion;
          let whereClause = {
            organizationId: Number(organizationId),
            enabled: true,
          };

          if (awsAccountId) {
            whereClause.awsAccount = {
              awsAccountId: awsAccountId,
            };
          }

          if (awsRegion) {
            whereClause.awsRegion = {
              in: [awsRegion, "global"],
            };
          }

          let workspaces = await prisma.workspace.findMany({
            where: whereClause,
            select: {
              id: true,
              name: true,
              scanInterval: true,
              awsRegion: true,
              awsAccount: true,
              providerGroup: true,
            },
          });

          workspaces = workspaces
            .map(({ awsRegion, awsAccount, providerGroup }) => {
              // Check if awsAccount and providerGroup are not null or undefined
              if (awsAccount && providerGroup) {
                return {
                  root_folder: `finisterra/generated/aws/${awsAccount.awsAccountId}/${awsRegion}/`,
                  folder: `finisterra/generated/aws/${awsAccount.awsAccountId}/${awsRegion}/${providerGroup.code}`,
                  service_name: providerGroup.code,
                  aws_account_id: awsAccount.awsAccountId,
                  aws_region: awsRegion,
                  aws_iam_role:
                    awsAccount.roleArn ||
                    `arn:aws:iam::${awsAccount.awsAccountId}:role/ft-ro-gha-cicd-role`,
                };
              }
              return null;
            })
            .filter(Boolean);

          if (workspaces) {
            return res.status(200).json({
              workspaces: workspaces,
            });
          } else {
            return res.status(200).json({ workspaces: [], aws_iam_role: null });
          }
        }
      } catch (error) {
        return res.status(500).json({ message: error.message });
      }

    case "POST":
      try {
        const workspace = await prisma.workspace.create({
          data: {
            ...req.body,
            organizationId: Number(organizationId),
          },
          include: {
            awsAccount: true,
            providerGroup: true,
            awsStateConfig: true,
          },
        });

        return res.status(201).json({ workspace });
      } catch (error) {
        return res.status(500).json({ message: error.message });
      }

    case "PUT":
      const { id, ...rest } = req.body;

      if (!id) {
        return res.status(400).json({ message: "Missing workspace id" });
      }

      try {
        const workspace = await prisma.workspace.update({
          where: { id: Number(id) },
          data: {
            ...rest,
            organizationId: Number(organizationId),
          },
          include: {
            awsAccount: true,
            providerGroup: true,
            awsStateConfig: true,
          },
        });

        return res.status(200).json({ workspace });
      } catch (error) {
        return res.status(500).json({ message: error.message });
      }

    default:
      res.setHeader("Allow", ["GET", "POST", "PUT"]);
      res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
