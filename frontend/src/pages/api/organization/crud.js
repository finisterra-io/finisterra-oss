import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

export default async function handler(req, res) {
  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  if (req.method === "GET") {
    const { organizationId } = req.query;
    const organizationIdParam = parseInt(organizationId);

    const organization = await prisma.organization.findUnique({
      where: {
        id: organizationIdParam,
      },
    });

    await prisma.$disconnect();
    res.status(200).json(organization);
  } else if (req.method === "PUT") {
    const { organizationName, organizationId } = req.body;

    if (organizationId) {
      // Update existing organization
      const organizationIdParam = parseInt(organizationId);
      const updatedOrganization = await prisma.organization.update({
        where: {
          id: organizationIdParam,
        },
        data: {
          name: organizationName,
        },
      });

      await prisma.$disconnect();
      res.status(200).json(updatedOrganization);
    } else {
      const userId = session.user.id;
      const userEmail = session.user.email;

      // Create new organization
      const newOrganization = await prisma.organization.create({
        data: {
          name: organizationName,
          memberships: {
            create: {
              user: { connect: { id: userId } },
              role: "OWNER",
              membershipStatus: "ACTIVE",
            },
          },
          invitations: {
            create: {
              email: userEmail,
              user: { connect: { id: userId } },
              status: "ACCEPTED",
            },
          },
        },
      });

      await prisma.$disconnect();
      res.status(200).json(newOrganization);
    }
  } else {
    res.status(405).json({ error: "Method not allowed" });
  }
}
