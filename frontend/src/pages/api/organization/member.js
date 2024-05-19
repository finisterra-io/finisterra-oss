import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

async function handler(req, res) {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  const organizationId = session.organizationId;

  if (req.method === "GET") {
    const members = await prisma.$queryRaw`
    SELECT
      COALESCE("user".id, invitation.id) AS id,
      COALESCE("user".name, '') AS name,
      COALESCE("user".email, invitation.email) AS email,
      COALESCE(membership."role", NULL) AS role,
      COALESCE(membership."membershipStatus"::text, invitation."status"::text, 'PENDING') AS status
    FROM
      invitation
    FULL OUTER JOIN
      "user" ON invitation."email" = "user"."email" AND invitation."organizationId" = ${organizationId}
    LEFT JOIN
      membership ON membership."userId" = "user".id AND membership."organizationId" = ${organizationId}
    WHERE
      membership."organizationId" = ${organizationId} OR invitation."organizationId" = ${organizationId}
  `;

    res.status(200).json({ members });
  } else if (req.method === "DELETE") {
    const { id } = req.query;
    const parsedId = parseInt(id, 10);

    try {
      const member = await prisma.$queryRaw`
        SELECT
          COALESCE(invitation."status", NULL) AS status
        FROM
          invitation
        FULL OUTER JOIN
          "user" ON invitation."email" = "user"."email" AND invitation."organizationId" = ${organizationId}
        LEFT JOIN
          membership ON membership."userId" = "user".id AND membership."organizationId" = ${organizationId}
        WHERE
          COALESCE("user".id, invitation.id) = ${parsedId}
      `;

      if (member.length === 0) {
        res.status(404).json({ message: "Member not found" });
        return;
      }

      const status = member[0].status;

      if (status === "PENDING") {
        await prisma.invitation.delete({
          where: { id: parseInt(parsedId) },
        });
      } else {
        await prisma.membership.updateMany({
          where: {
            userId: parseInt(parsedId),
            organizationId: parseInt(organizationId),
          },
          data: { membershipStatus: "INACTIVE" },
        });
      }
      res
        .status(200)
        .json({ message: "Member deleted or deactivated successfully" });
    } catch (error) {
      console.error("Error deleting or deactivating member:", error);
      res
        .status(500)
        .json({ message: "Error deleting or deactivating member" });
    }
  } else if (req.method === "PUT") {
    const { id } = req.query;
    const parsedId = parseInt(id, 10);

    try {
      const result = await prisma.membership.updateMany({
        where: {
          userId: parseInt(parsedId),
          organizationId: parseInt(organizationId),
        },
        data: { membershipStatus: "ACTIVE" },
      });

      if (result.count > 0) {
        res.status(200).json({ message: "Member activated successfully" });
      } else {
        res.status(404).json({ message: "Member not found" });
      }
    } catch (error) {
      console.error("Error activating member:", error);
      res.status(500).json({ message: "Error activating member" });
    }
  } else if (req.method === "PUT") {
    const { id } = req.query;
    const parsedId = parseInt(id, 10);

    try {
      const result = await prisma.membership.updateMany({
        where: {
          userId: parseInt(parsedId),
          organizationId: parseInt(organizationId),
        },
        data: { membershipStatus: "ACTIVE" },
      });

      if (result.count > 0) {
        res.status(200).json({ message: "Member activated successfully" });
      } else {
        res.status(404).json({ message: "Member not found" });
      }
    } catch (error) {
      console.error("Error activating member:", error);
      res.status(500).json({ message: "Error activating member" });
    }
  } else if (req.method === "PUT") {
    const { id } = req.query;
    const parsedId = parseInt(id, 10);

    try {
      const result = await prisma.membership.updateMany({
        where: {
          userId: parseInt(parsedId),
          organizationId: parseInt(organizationId),
        },
        data: { membershipStatus: "ACTIVE" },
      });

      if (result.count > 0) {
        res.status(200).json({ message: "Member activated successfully" });
      } else {
        res.status(404).json({ message: "Member not found" });
      }
    } catch (error) {
      console.error("Error activating member:", error);
      res.status(500).json({ message: "Error activating member" });
    }
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}
export default handler;
