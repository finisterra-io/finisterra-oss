import { PrismaClient } from "@prisma/client";
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

const prisma = new PrismaClient();

export default async function handle(req, res) {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    return res.status(403).json({ error: "User not authenticated" });
  }

  if (req.method === "GET") {
    try {
      const freeTierLimit = 1;
      const enabledAwsAccountsCount = await prisma.awsAccount.count({
        where: {
          organizationId: session.organizationId,
          enabled: true,
          region: {
            not: "global",
          },
        },
      });
      const aws = {
        provider: "AWS",
        accounts: enabledAwsAccountsCount - freeTierLimit,
        price: 190,
      };
      let usage = [aws];
      return res.json({ usage });
    } catch (error) {
      console.error("Error fetching Usage:", error);
      return res.status(500).json({ error: "Failed to fetch Usage" });
    }
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}
