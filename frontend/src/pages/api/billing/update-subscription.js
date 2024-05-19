import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";
import { updateSubscription } from "utils/billing/subscription";

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

  if (session) {
    organizationId = session.organizationId;
  } else {
    organizationId = validKey.organizationId;
  }

  switch (req.method) {
    case "POST":
      try {
        updateSubscription({ organizationId });
        return res.status(201).json({ message: "Subscription updated" });
      } catch (error) {
        return res.status(500).json({ message: error.message });
      }

    default:
      res.setHeader("Allow", ["POST"]);
      res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
