// next
import NextAuth from "next-auth";

import Auth0Provider from "next-auth/providers/auth0";
import CredentialsProvider from "next-auth/providers/credentials";
import CognitoProvider from "next-auth/providers/cognito";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";

import jwt from "jsonwebtoken";

import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

// third-party
import axios from "axios";

export let users = [
  {
    id: 1,
    name: "Jone Doe",
    email: "info@codedthemes.com",
    password: "123456",
  },
];

/**
 * Takes a token, and returns a new token with updated
 * `accessToken` and `accessTokenExpires`. If an error occurs,
 * returns the old token and an error property
 */
async function refreshAccessToken(token) {
  try {
    const url =
      "https://oauth2.googleapis.com/token?" +
      new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID,
        client_secret: process.env.GOOGLE_CLIENT_SECRET,
        grant_type: "refresh_token",
        refresh_token: token.refreshToken,
      });

    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      method: "POST",
    });

    const refreshedTokens = await response.json();

    if (!response.ok) {
      throw refreshedTokens;
    }

    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
      refreshToken: refreshedTokens.refresh_token ?? token.refreshToken, // Fall back to old refresh token
    };
  } catch (error) {
    console.log(error);

    return {
      ...token,
      error: "RefreshAccessTokenError",
    };
  }
}

export const authOptions = {
  secret: process.env.NEXTAUTH_SECRET_KEY,
  providers: [
    // Auth0Provider({
    //   name: "Auth0",
    //   clientId: process.env.AUTH0_CLIENT_ID,
    //   clientSecret: process.env.AUTH0_CLIENT_SECRET,
    //   issuer: `https://${process.env.AUTH0_DOMAIN}`,
    // }),
    // CognitoProvider({
    //   name: "Cognito",
    //   clientId: process.env.COGNITO_CLIENT_ID,
    //   clientSecret: process.env.COGNITO_CLIENT_SECRET,
    //   issuer: `https://cognito-idp.${process.env.COGNITO_REGION}.amazonaws.com/${process.env.COGNITO_POOL_ID}`,
    // }),

    GoogleProvider({
      name: "Google",
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
        },
      },
    }),
    // GitHubProvider({
    //   name: "Github",
    //   clientId: process.env.GITHUB_ID,
    //   clientSecret: process.env.GITHUB_SECRET,
    // }),
    // // functionality provided for credentials based authentication is intentionally limited to discourage use of passwords due to the
    // // inherent security risks associated with them and the additional complexity associated with supporting usernames and passwords.
    // // We recommend to ignore credential based auth unless its super necessary
    // // Ref: https://next-auth.js.org/providers/credentials
    // // https://github.com/nextauthjs/next-auth/issues/3562
    // CredentialsProvider({
    //   id: "login",
    //   name: "Login",
    //   credentials: {
    //     email: { label: "Email", type: "email", placeholder: "Enter Email" },
    //     password: {
    //       label: "Password",
    //       type: "password",
    //       placeholder: "Enter Password",
    //     },
    //   },
    //   async authorize(credentials) {
    //     try {
    //       const user = await axios.post(
    //         `${process.env.NEXTAUTH_URL}/api/auth/login`,
    //         {
    //           password: credentials?.password,
    //           email: credentials?.email,
    //         }
    //       );

    //       if (user) {
    //         return user.data;
    //       }
    //     } catch (e) {
    //       const errorMessage = e?.response.data.message;
    //       throw new Error(errorMessage);
    //     }
    //   },
    // }),
    // // functionality provided for credentials based authentication is intentionally limited to discourage use of passwords due to the
    // // inherent security risks associated with them and the additional complexity associated with supporting usernames and passwords.
    // // We recommend to ignore credential based auth unless its super necessary
    // // Ref: https://next-auth.js.org/providers/credentials
    // // https://github.com/nextauthjs/next-auth/issues/3562
    // CredentialsProvider({
    //   id: "register",
    //   name: "Register",
    //   credentials: {
    //     name: { label: "Name", type: "text", placeholder: "Enter Name" },
    //     email: { label: "Email", type: "email", placeholder: "Enter Email" },
    //     password: {
    //       label: "Password",
    //       type: "password",
    //       placeholder: "Enter Password",
    //     },
    //   },
    //   async authorize(credentials) {
    //     try {
    //       const user = await axios.post(
    //         `${process.env.NEXTAUTH_URL}/api/auth/register`,
    //         {
    //           name: credentials?.name,
    //           password: credentials?.password,
    //           email: credentials?.email,
    //         }
    //       );

    //       if (user) {
    //         users.push(user.data);
    //         return user.data;
    //       }
    //     } catch (e) {
    //       const errorMessage = e?.response.data.message;
    //       throw new Error(errorMessage);
    //     }
    //   },
    // }),
  ],
  callbacks: {
    async jwt({ token, trigger, session, user, account, profile }) {
      if (user && account) {
        const dbUser = await prisma.user.findFirst({
          where: { email: user.email },
        });
        token.user_id = dbUser.id;
        token.id = user.id;
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        token.idTokenExpires = Date.now() + account.expires_in * 1000;
        token.refreshToken = account.refresh_token;
        token.provider = account?.provider;
      }
      // Return previous token if the access token has not expired yet
      if (Date.now() < token.accessTokenExpires) {
        return token;
      }

      // Access token has expired, try to update it
      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      if (token) {
        session.id = token.id;
        session.provider = token.provider;
        session.tocken = token;
        session.accessToken = token.accessToken;
        session.idToken = token.idToken;
        session.idTokenExpires = token.idTokenExpires;
        const userId = token.user_id;
        session.user.id = token.user_id;
        try {
          const membership = await prisma.membership.findFirst({
            where: { userId, membershipStatus: "ACTIVE" },
            include: { organization: true },
          });

          session.organizationId = membership
            ? membership.organizationId
            : null;
          session.organizationName = membership
            ? membership.organization.name
            : null;

          // Assuming 'session.user.email' is in the format 'username@domain.com'
          // Known email providers
          const knownProviders = [
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "msn.com",
            "live.com",
            "aol.com",
            "icloud.com",
            "mail.com",
            "zoho.com",
            "yandex.com",
            "protonmail.com",
          ];

          if (session.organizationId == null) {
            const emailParts = session.user.email.split("@");
            const domainWithTLD = emailParts[1];
            const domain = emailParts[1].split(".")[0];

            // Check if the domain with TLD is in the list of known providers
            const isKnownProvider = knownProviders.includes(
              domainWithTLD.toLowerCase()
            );

            // Use 'setmeup' if the domain is a known provider, else use the domain as the name
            const organizationName = isKnownProvider
              ? "setmeup"
              : domain.charAt(0).toUpperCase() + domain.slice(1);

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
                    email: session.user.email,
                    user: { connect: { id: userId } },
                    status: "ACCEPTED",
                  },
                },
              },
            });
          }

          //Check if there are awsAccounts setup
          const count = await prisma.awsAccount.count({
            where: {
              organizationId: session.organizationId,
            },
          });
          session.accountsSetup = count > 0;

          const state = jwt.sign(
            { organizationId: session.organizationId },
            process.env.JWT_SECRET
          );
          session.state = state;
        } catch (error) {
          console.error(
            "Error fetching organization in session callback:",
            error
          );
        }
      }
      return session;
    },
    // async redirect({ url, baseUrl }) {
    //   console.log("redirect", url, baseUrl);
    //   return url;
    // },
    async signIn({ user, account, profile, email, credentials }) {
      // Check if the user already exists in the database
      const existingUser = await prisma.user.findUnique({
        where: { email: user.email },
      });

      const refreshToken = account?.refresh_token;

      if (existingUser) {
        if (existingUser.status === "INACTIVE") {
          return false;
        } else {
          // If user exists and is active, update refreshToken
          await prisma.user.update({
            where: { email: user.email },
            data: { refreshToken },
          });
        }
      } else {
        // If the user doesn't exist, create a new user in the database
        const createdUser = await prisma.user.create({
          data: {
            name: user.name,
            email: user.email,
            refreshToken,
          },
        });

        // Check if there are any pending invitations for the new user
        const pendingInvitations = await prisma.invitation.findMany({
          where: {
            email: user.email,
            status: "PENDING",
          },
        });

        // If there are pending invitations, accept them and update the membership table
        if (pendingInvitations.length > 0) {
          for (const invitation of pendingInvitations) {
            await prisma.membership.create({
              data: {
                userId: createdUser.id,
                organizationId: invitation.organizationId,
                role: invitation.role,
              },
            });

            // Update the invitation status to "ACCEPTED"
            await prisma.invitation.update({
              where: { id: invitation.id },
              data: { status: "ACCEPTED" },
            });
          }
        }
      }

      // Return true to sign the user in
      return true;
    },
  },
  session: {
    strategy: "jwt",
    maxAge: Number(process.env.JWT_TIMEOUT),
  },
  jwt: {
    secret: process.env.JWT_SECRET,
  },
  pages: {
    signIn: "/login",
    newUser: "/register",
  },
};

export default NextAuth(authOptions);
