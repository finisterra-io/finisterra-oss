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
      // Fetch the active subscription for the organization
      const activeSubscription = await prisma.subscription.findFirst({
        where: {
          organizationId: organizationId,
          status: "active", // Ensure you're fetching the currently active subscription
        },
      });

      if (!activeSubscription) {
        return res.status(404).json({ error: "Active subscription not found" });
      }

      // Proceed to update the subscription in Stripe
      await stripe.subscriptions.update(
        activeSubscription.stripeSubscriptionId,
        {
          cancel_at_period_end: true,
        }
      );

      // Update the subscription status in your database
      await prisma.subscription.update({
        where: { id: activeSubscription.id }, // Use primary key for precision
        data: { status: "pending_cancellation" }, // Adjust based on your status values
      });

      // Optionally, update your organization's record
      await prisma.organization.update({
        where: { id: organizationId },
        data: { subscriptionActive: false },
      });

      res
        .status(200)
        .json({ message: "Subscription set to cancel at period end" });
    } catch (error) {
      console.error("Error cancelling subscription:", error);
      res.status(500).json({ error: "Failed to cancel subscription" });
    }
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}
