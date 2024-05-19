import { PrismaClient } from "@prisma/client";
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

const prisma = new PrismaClient();

export default async function handle(req, res) {
  // Ensure that only GET requests are handled
  if (req.method !== 'GET') {
    return res.status(405).json({ message: "Method Not Allowed" });
  }
  
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
  
  try {
    const organization = await prisma.organization.findUnique({
      where: { id: organizationId },
    });
    
    const provider = req.query.provider;
    
    let hasActiveSubscription = false;
    if (organization && organization.subscriptionActive) {
      hasActiveSubscription = true;
    }
    
    if ( provider !== "aws" ) {
      const enabledAwsAccountsCount = await prisma.awsAccount.count({
        where: {
          organizationId: organizationId,
          enabled: true,
          region: {
            not: "global",
          },
        },
      });
      return res.json({
        hasActiveSubscription: hasActiveSubscription,
        usage: enabledAwsAccountsCount,
      });
    }
    else {
      // Return true for any other providers
      return res.json({
        hasActiveSubscription: hasActiveSubscription,
        usage: 0,
      });
    }
  } catch (error) {
    console.error("Error fetching subscription status:", error);
    return res
    .status(500)
    .json({ error: "Failed to fetch subscription status" });
  }
}
