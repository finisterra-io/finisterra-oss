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

      // Find the workspace in the database
      const workspace = await prisma.workspace.findFirst({
        where: {
          organizationId: Number(organizationId),
          id: parseInt(workspaceId),
        },
        include: {
          awsAccount: true,
          awsStateConfig: true,
          providerGroup: true,
        },
      });

      // If the workspace was not found, return a 404 error
      if (!workspace) {
        res.status(404).json({ message: "Workspace not found" });
        return;
      }
      res.status(200).json(workspace);
    } else {
      // If the request is not a GET request, return an error
      res.setHeader("Allow", ["GET"]);
      res.status(405).end(`Method ${req.method} Not Allowed`);
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
