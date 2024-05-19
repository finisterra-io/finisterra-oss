import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

const withAuthenticated = (handler) => async (req, res) => {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  const memberships = await prisma.membership.findMany({
    where: {
      userId: session.user.id,
    },
    select: {
      organizationId: true,
      membershipStatus: true,
    },
  });

  const currentOrganizationMembership = memberships.find(
    (membership) => membership.organizationId === session.organizationId
  );

  if (
    currentOrganizationMembership &&
    currentOrganizationMembership.membershipStatus === "INACTIVE"
  ) {
    res.setHeader(
      "Set-Cookie",
      `next-auth.session-token=; Max-Age=0; Path=/; HttpOnly`
    );
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  return handler(req, res);
};

export default withAuthenticated;
