import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";
import sgMail from "@sendgrid/mail";

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

export default async function createInvitation(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ message: "Method not allowed" });
  }
  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  const { email, role } = req.body;
  const organizationId = session.organizationId;

  try {
    let invitation = await prisma.invitation.findUnique({ where: { email } });

    if (!invitation) {
      invitation = await prisma.invitation.create({
        data: {
          email,
          role,
          organization: { connect: { id: organizationId } },
        },
      });
    }

    // Send the invitation email
    const msg = {
      to: email,
      from: "eng@finisterra.io",
      subject: "Invitation to join the organization",
      text: `You have been invited to join the organization. Click the link to accept the invitation: ${process.env.APP_URL}`,
      html: `<p>You have been invited to join the organization. <a href="${process.env.APP_URL}">Click here</a> to accept the invitation.</p>`,
    };

    await sgMail.send(msg);

    return res.status(200).json({ invitation });
  } catch (error) {
    console.error("Error creating invitation:", error);
    return res.status(500).json({ message: "Error creating invitation" });
  }
}
