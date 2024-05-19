import { PrismaClient } from "@prisma/client";
import crypto from "crypto";
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

const prisma = new PrismaClient();

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
  let userId;

  if (session) {
    organizationId = session.organizationId;
    userId = session.user.id;
  } else {
    organizationId = validKey.organizationId;
    userId = validKey.userId;
  }

  if (req.method === "POST") {
    const { name, description } = req.body;
    const apiKey = crypto.randomBytes(32).toString("hex");

    // Check if an API key with the same name already exists
    const existingApiKey = await prisma.apiKey.findFirst({
      where: {
        name: name,
        organizationId: organizationId,
      },
    });

    if (existingApiKey) {
      existingApiKey.new = false;
      // API key with the same name already exists. Return it.
      return res.json({ createdApiKey: existingApiKey });
    } else {
      // No API key with the same name exists. Create a new one.
      try {
        const createdApiKey = await prisma.apiKey.create({
          data: {
            key: apiKey,
            name: name,
            description: description,
            userId: userId,
            organizationId: organizationId,
          },
        });

        return res.json({ createdApiKey });
      } catch (error) {
        // Handle error, for example log it and return an error response
        console.error("Error creating API key:", error);
        return res.status(500).json({ error: "Internal Server Error" });
      }
    }
  } else if (req.method === "GET") {
    try {
      const apiKeys = await prisma.apiKey.findMany({
        where: { organizationId: organizationId },
      });
      return res.json({ apiKeys });
    } catch (error) {
      console.error("Error fetching API keys:", error);
      return res.status(500).json({ error: "Failed to fetch API keys" });
    }
  } else if (req.method === "DELETE") {
    const { id } = req.query;

    try {
      await prisma.apiKey.delete({
        where: { id: parseInt(id, 10) },
      });

      return res.status(204).send();
    } catch (error) {
      console.error("Error deleting API key:", error);
      return res.status(500).json({ error: "Failed to delete API key" });
    }
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}
