const { PrismaClient } = require("@prisma/client");
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

const prisma = new PrismaClient();

export default async function handle(req, res) {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  const { providerName } = req.query;

  if (req.method === "GET") {
    try {
      const provider = await prisma.provider.findUnique({
        where: { name: providerName }, // use providerName in the where clause
        include: {
          ProviderGroup: {
            where: { active: true },
          },
        },
      });

      if (!provider) {
        return res
          .status(404)
          .json({ error: `${providerName} provider not found` });
      }

      return res.status(200).json(provider.ProviderGroup);
    } catch (err) {
      console.error(err);
      return res
        .status(500)
        .json({ error: "An error occurred while retrieving groups" });
    }
  } else {
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
