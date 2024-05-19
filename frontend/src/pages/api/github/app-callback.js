const { PrismaClient } = require("@prisma/client");
import url from "url";

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

const prisma = new PrismaClient();

export default async (req, res) => {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    return res.status(401).json({ message: "Unauthorized" });
  }

  if (req.method === "GET") {
    const query = url.parse(req.url, true).query;

    try {
      const organizationId = session.organizationId;

      const githubAccount = await prisma.githubAccount.upsert({
        where: { organizationId: organizationId },
        update: {
          organizationId: organizationId,
          installationId: parseInt(query.installation_id, 10),
        },
        create: {
          installationId: parseInt(query.installation_id, 10),
          organization: {
            connect: { id: organizationId },
          },
        },
      });

      res.status(200).json(githubAccount);
    } catch (error) {
      console.error(error);
      res.status(500).end("Error exchanging code for token");
    }
  } else {
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};
