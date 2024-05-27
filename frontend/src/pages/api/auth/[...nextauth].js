import NextAuth from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import CredentialsProvider from 'next-auth/providers/credentials';
import { PrismaClient } from '@prisma/client';
import axios from 'axios';
import jwt from 'jsonwebtoken';

const prisma = new PrismaClient();

async function refreshAccessToken(token) {
  try {
    const url =
      "https://oauth2.googleapis.com/token?" +
      new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID,
        client_secret: process.env.GOOGLE_CLIENT_SECRET,
        grant_type: 'refresh_token',
        refresh_token: token.refreshToken,
      });

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      method: 'POST',
    });

    const refreshedTokens = await response.json();

    if (!response.ok) {
      throw refreshedTokens;
    }

    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
      refreshToken: refreshedTokens.refresh_token ?? token.refreshToken,
    };
  } catch (error) {
    console.log(error);

    return {
      ...token,
      error: 'RefreshAccessTokenError',
    };
  }
}

export const authOptions = {
  secret: process.env.NEXTAUTH_SECRET_KEY,
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          prompt: 'consent',
          access_type: 'offline',
          response_type: 'code',
        },
      },
    }),
    CredentialsProvider({
      id: 'login',
      name: 'Login',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'Enter Email' },
        password: {
          label: 'Password',
          type: 'password',
          placeholder: 'Enter Password',
        },
      },
      async authorize(credentials) {
        try {
          const user = await axios.post(
            `${process.env.NEXTAUTH_URL}/api/auth/login`,
            {
              email: credentials?.email,
              password: credentials?.password,
            }
          );

          if (user) {
            return user.data;
          }
        } catch (e) {
          const errorMessage = e?.response?.data?.message;
          throw new Error(errorMessage);
        }
      },
    }),
    CredentialsProvider({
      id: 'register',
      name: 'Register',
      credentials: {
        name: { label: 'Name', type: 'text', placeholder: 'Enter Name' },
        email: { label: 'Email', type: 'email', placeholder: 'Enter Email' },
        password: {
          label: 'Password',
          type: 'password',
          placeholder: 'Enter Password',
        },
      },
      async authorize(credentials) {
        try {
          const user = await axios.post(
            `${process.env.NEXTAUTH_URL}/api/auth/register`,
            {
              name: credentials?.name,
              email: credentials?.email,
              password: credentials?.password,
            }
          );

          if (user) {
            return user.data;
          }
        } catch (e) {
          const errorMessage = e?.response?.data?.message;
          throw new Error(errorMessage);
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      if (user && account) {
        const dbUser = await prisma.user.findUnique({
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
      if (Date.now() < token.accessTokenExpires) {
        return token;
      }
      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      session.id = token.id;
      session.provider = token.provider;
      session.token = token;
      session.accessToken = token.accessToken;
      session.idToken = token.idToken;
      session.idTokenExpires = token.idTokenExpires;
      session.user.id = token.user_id;

      const userId = token.user_id;
      try {
        const membership = await prisma.membership.findFirst({
          where: { userId, membershipStatus: 'ACTIVE' },
          include: { organization: true },
        });

        session.organizationId = membership
          ? membership.organizationId
          : null;
        session.organizationName = membership
          ? membership.organization.name
          : null;

        const knownProviders = [
          'gmail.com',
          'yahoo.com',
          'hotmail.com',
          'outlook.com',
          'msn.com',
          'live.com',
          'aol.com',
          'icloud.com',
          'mail.com',
          'zoho.com',
          'yandex.com',
          'protonmail.com',
        ];

        if (!session.organizationId) {
          const emailParts = session.user.email.split('@');
          const domainWithTLD = emailParts[1];
          const domain = emailParts[1].split('.')[0];

          const isKnownProvider = knownProviders.includes(
            domainWithTLD.toLowerCase()
          );

          const organizationName = isKnownProvider
            ? 'setmeup'
            : domain.charAt(0).toUpperCase() + domain.slice(1);

          const newOrganization = await prisma.organization.create({
            data: {
              name: organizationName,
              memberships: {
                create: {
                  user: { connect: { id: userId } },
                  role: 'OWNER',
                  membershipStatus: 'ACTIVE',
                },
              },
              invitations: {
                create: {
                  email: session.user.email,
                  user: { connect: { id: userId } },
                  status: 'ACCEPTED',
                },
              },
            },
          });

          session.organizationId = newOrganization.id;
          session.organizationName = newOrganization.name;
        }

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
          'Error fetching organization in session callback:',
          error
        );
      }
      return session;
    },
    async signIn({ user, account }) {
      const existingUser = await prisma.user.findUnique({
        where: { email: user.email },
      });

      const refreshToken = account?.refresh_token;

      if (existingUser) {
        if (existingUser.status === 'INACTIVE') {
          return false;
        } else {
          await prisma.user.update({
            where: { email: user.email },
            data: { refreshToken },
          });
        }
      } else {
        const createdUser = await prisma.user.create({
          data: {
            name: user.name,
            email: user.email,
            refreshToken,
          },
        });

        const pendingInvitations = await prisma.invitation.findMany({
          where: {
            email: user.email,
            status: 'PENDING',
          },
        });

        if (pendingInvitations.length > 0) {
          for (const invitation of pendingInvitations) {
            await prisma.membership.create({
              data: {
                userId: createdUser.id,
                organizationId: invitation.organizationId,
                role: invitation.role,
              },
            });

            await prisma.invitation.update({
              where: { id: invitation.id },
              data: { status: 'ACCEPTED' },
            });
          }
        }
      }
      return true;
    },
  },
  session: {
    strategy: 'jwt',
    maxAge: Number(process.env.JWT_TIMEOUT),
  },
  jwt: {
    secret: process.env.JWT_SECRET,
  },
  pages: {
    signIn: '/login',
    newUser: '/register',
  },
};

export default NextAuth(authOptions);
