import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

export default async function handle(req, res) {
  if (req.method === "GET") {
    const session = await getServerSession(req, res, authOptions);

    if (!session) {
      res.status(401).json({ message: "Unauthorized" });
      return;
    }

    const organizationId = session.organizationId;

    // Construct where clause dynamically
    const whereClause = {
      organizationId: Number(organizationId),
    };

    if (req.body && req.body.workspaceId) {
      whereClause.workspaceId = Number(req.body.workspaceId);
    }

    const resources = await prisma.resource.findMany({
      where: whereClause,
      include: {
        organization: true,
        workspace: true,
      },
    });

    res.status(200).json({ resources });
  } else {
    // Handle other request methods such as POST, DELETE, etc.
    res.status(405).json({ message: "Method not allowed" });
  }
}
