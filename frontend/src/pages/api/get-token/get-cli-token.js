import { PrismaClient } from "@prisma/client";
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

const prisma = new PrismaClient();

export default async function handle(req, res) {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    return res.status(403).json({ error: "User not authenticated" });
  }

  const organizationId = session.organizationId;
  const userId = session.user.id;

  if (req.method === "GET") {
    try {
      // Fetch the API key for the user's organization
      const apiKey = await prisma.apiKey.findFirst({
        where: {
          organizationId: organizationId,
          userId: userId,
        },
        orderBy: {
          createdAt: "desc", // Example: get the most recently created key
        },
      });

      if (!apiKey) {
        return res
          .status(404)
          .json({ error: "API key not found for the user's organization." });
      }

      res.status(200).json({ token: apiKey.key });
    } catch (error) {
      console.error("Error fetching API key:", error);
      return res.status(500).json({ error: "Failed to fetch API key" });
    }
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}
