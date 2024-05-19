import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

export default async function handler(req, res) {
  try {
    // Check if the user is authenticated using Next-auth
    const session = await getServerSession(req, res, authOptions);
    if (!session) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }
    const organizationId = session.organizationId;

    if (req.method === "GET") {
      const { code } = req.query;

      const workspaces = await prisma.workspace.findMany({
        where: {
          organizationId: Number(organizationId),
          enabled: true,
          providerGroup: {
            code: code,
          },
        },
        select: {
          id: true,
          name: true,
          awsAccount: {
            select: {
              id: true,
              awsAccountId: true,
              name: true,
            },
          },
        },
      });

      //   res.json(workspaces);

      res.status(200).json(workspaces);
    } else {
      res.setHeader("Allow", ["GET"]);
      res.status(405).end(`Method ${req.method} Not Allowed`);
    }
  } catch (error) {
    console.error(error);
    res
      .status(500)
      .json({ message: "Internal server error", error: error.message });
  } finally {
    await prisma.$disconnect();
  }
}
