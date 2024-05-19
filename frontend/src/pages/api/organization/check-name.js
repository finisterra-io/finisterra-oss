import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

export default async function handler(req, res) {
  if (req.method === "GET") {
    const session = await getServerSession(req, res, authOptions);

    if (!session) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }

    const { orgName } = req.query;

    const existingOrganization = await prisma.organization.findFirst({
      where: {
        name: orgName,
      },
    });

    await prisma.$disconnect();
    res.status(200).json({ exists: !!existingOrganization });
  } else {
    res.status(405).json({ error: "Method not allowed" });
  }
}
