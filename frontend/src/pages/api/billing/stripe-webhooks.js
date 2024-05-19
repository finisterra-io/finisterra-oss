import { buffer } from "micro";
import Stripe from "stripe";
import { PrismaClient } from "@prisma/client";
import getRawBody from "raw-body";

const prisma = new PrismaClient();
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export const config = {
  api: {
    bodyParser: false,
  },
};

const webhookHandler = async (req, res) => {
  if (req.method === "POST") {
    let event;

    const sig = req.headers["stripe-signature"];

    try {
      const rawBody = await getRawBody(req);
      event = stripe.webhooks.constructEvent(
        rawBody,
        sig,
        process.env.STRIPE_WEBHOOK_SECRET
      );
    } catch (err) {
      console.error(`Webhook signature verification failed.`, err.message);
      return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    if (event.type === "checkout.session.completed") {
      const session = event.data.object;

      try {
        // Retrieve the organization based on the Stripe customer ID
        const organization = await prisma.organization.findFirst({
          where: {
            stripeCustomerId: session.customer,
          },
        });

        if (!organization) {
          console.error(
            `Organization with Stripe customer ID ${session.customer} not found.`
          );
          return res.status(404).send("Organization not found");
        }

        // Update or create a subscription record
        await prisma.subscription.upsert({
          where: { stripeSubscriptionId: session.subscription },
          update: { status: "active" },
          create: {
            organizationId: organization.id,
            stripeSubscriptionId: session.subscription,
            status: "active",
          },
        });

        // Optionally update the organization's subscriptionActive flag
        await prisma.organization.update({
          where: { id: organization.id },
          data: { subscriptionActive: true },
        });

        console.log(
          `Subscription for organization ${organization.id} is now active.`
        );
      } catch (error) {
        console.error("Failed to update database", error);
        return res.status(500).send("Failed to update database");
      }
    }

    res.json({ received: true });
  } else {
    res.setHeader("Allow", "POST");
    res.status(405).end("Method Not Allowed");
  }
};

export default webhookHandler;
