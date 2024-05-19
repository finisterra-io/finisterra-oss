import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

export default async function handler(req, res) {
  try {
    // Check if the user is authenticated using Next-auth
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

    if (req.method === "GET") {
      // Handle GET requests
      const { awsAccountId } = req.query;

      // Find the AWS Account in the database
      const awsAccount = await prisma.awsAccount.findFirst({
        where: {
          id: parseInt(awsAccountId),
          organizationId: Number(organizationId),
        },
      });

      // If the AWS Account was not found, return a 404 error
      if (!awsAccount) {
        res.status(404).json({ message: "AWS Account not found" });
        return;
      }

      // Return the AWS Account details
      res.status(200).json(awsAccount);
    } else {
      // If the request is not a GET or POST request, return an error
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
