import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const userId = parseInt(req.query.userId, 10);

  try {
    const user = await prisma.user.findUnique({
      where: { id: userId },
      include: {
        memberships: {
          where: { membershipStatus: "ACTIVE" },
          include: {
            organization: true,
          },
        },
      },
    });

    if (!user) {
      return res.status(404).json({ success: false, error: "User not found" });
    }

    const currentOrganization =
      user.memberships.length > 0 ? user.memberships[0].organization : null;

    if (currentOrganization) {
      return res
        .status(200)
        .json({ success: true, organization: currentOrganization });
    } else {
      return res.status(200).json({
        success: false,
        error: "Current organization not found or user is not an ACTIVE member",
      });
    }
  } catch (error) {
    console.error("Error getting current organization:", error);
    return res
      .status(500)
      .json({ success: false, error: "Internal server error" });
  }
}
