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
      // Handle GET requests
      // Extract the workspaceId from the request
      const { workspaceId } = req.query;

      if (!workspaceId) {
        return res
          .status(400)
          .json({ message: "Missing workspaceId parameter." });
      }

      const instances = await prisma.terraformModuleInstance.findMany({
        where: {
          workspaceId: Number(workspaceId),
        },
        include: {
          terraformModule: true, // Include the related TerraformModule data.
        },
      });

      return res.status(200).json(instances);
    }
  } catch (error) {
    // Log the error and return a server error response
    console.error(error);
    res
      .status(500)
      .json({ message: "Internal server error", error: error.message });
  } finally {
    // Ensure Prisma client gets disconnected
    await prisma.$disconnect();
  }
}
