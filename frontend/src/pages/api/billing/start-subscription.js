import { PrismaClient } from "@prisma/client";
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";
import Stripe from "stripe";

const prisma = new PrismaClient();
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export default async function handle(req, res) {
  const session = await getServerSession(req, res, authOptions);

  if (!session) {
    return res.status(403).json({ error: "User not authenticated" });
  }

  const organizationId = session.organizationId;

  if (!organizationId) {
    return res
      .status(400)
      .json({ message: "Missing organizationId in the session" });
  }

  if (req.method === "POST") {
    try {
      // Retrieve the user's organization from the database
      const organization = await prisma.organization.findUnique({
        where: {
          id: organizationId,
        },
      });

      if (!organization) {
        return res.status(404).json({ error: "Organization not found" });
      }

      let stripeCustomerId = organization.stripeCustomerId;
      if (!stripeCustomerId) {
        const stripeCustomer = await stripe.customers.create({
          email: session.user.email, // Correct use of session here
          name: organization.name,
        });
        stripeCustomerId = stripeCustomer.id;

        // Save the Stripe customer ID in your database
        await prisma.organization.update({
          where: { id: organization.id },
          data: {
            stripeCustomerId: stripeCustomerId,
            billingEmail: session.user.email,
          },
        });
      }

      // Create the subscription on Stripe using Checkout Sessions
      const checkoutSession = await stripe.checkout.sessions.create({
        // Renamed variable here
        payment_method_types: ["card"],
        line_items: [
          {
            price: process.env.STRIPE_PRICE_ID,
            quantity: 1,
          },
        ],
        mode: "subscription",
        success_url: `${process.env.NEXT_PUBLIC_BASE_URL}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${process.env.NEXT_PUBLIC_BASE_URL}/billing/cancel`,
        customer: stripeCustomerId,
      });

      res.status(200).json({ sessionId: checkoutSession.id }); // Use renamed variable here
    } catch (error) {
      console.error("Error starting subscription:", error);
      res.status(500).json({ error: "Failed to start subscription" });
    }
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}
