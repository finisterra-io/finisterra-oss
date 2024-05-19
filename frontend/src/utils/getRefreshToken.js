import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export async function getRefreshToken(email) {
  // Get the user session

  // Fetch user from the database using the session's user email
  const user = await prisma.user.findUnique({
    where: { email: email },
  });

  if (!user) {
    throw new Error("User not found");
  }

  // Return the refreshToken
  return user.refreshToken;
}
