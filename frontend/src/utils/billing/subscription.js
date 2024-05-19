import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export async function updateSubscription({ organizationId }) {
  const activeSubscription = await prisma.subscription.findFirst({
    where: {
      organizationId: organizationId,
      status: "active",
    },
  });
  if (!activeSubscription) {
    console.log("Active subscription not found");
    return false;
  }

  let subscriptionItemId = null;
  const subscription = await stripe.subscriptions.retrieve(
    activeSubscription.stripeSubscriptionId
  );
  subscriptionItemId = subscription.items.data[0].id;

  if (!subscriptionItemId) {
    console.log("Subscription item not found");
    return false;
  }

  const enabledAwsAccountsCount = await prisma.awsAccount.count({
    where: {
      organizationId: organizationId,
      enabled: true,
      region: {
        not: "global",
      },
    },
  });

  const freeTierLimit = 1;

  const updatedQuantity = Math.max(0, enabledAwsAccountsCount - freeTierLimit);

  await stripe.subscriptionItems.update(subscriptionItemId, {
    quantity: updatedQuantity,
  });
}
