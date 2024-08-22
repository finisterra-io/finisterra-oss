// pages/api/auth/reset-password.js

import { PrismaClient } from '@prisma/client';
import AWS from 'aws-sdk';

const prisma = new PrismaClient();

// Configure AWS SDK
AWS.config.update({
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  region: process.env.AWS_REGION,
});

const ses = new AWS.SES({ apiVersion: '2010-12-01' });

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ message: 'Email is required' });
  }

  try {
    const user = await prisma.user.findUnique({
      where: { email },
    });

    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    // Create a token and expiration time (e.g., 1 hour)
    const token = Math.random().toString(36).substr(2);
    const tokenExpiry = new Date(Date.now() + 3600000); // 1 hour

    // Save the token and expiry to the user
    await prisma.user.update({
      where: { email },
      data: {
        resetToken: token,
        resetTokenExpiry: tokenExpiry,
      },
    });

    const resetUrl = `${process.env.NEXTAUTH_URL}/reset-password?token=${token}&email=${email}`;

    const params = {
      Destination: {
        ToAddresses: [email],
      },
      Message: {
        Body: {
          Html: {
            Charset: "UTF-8",
            Data: `<p>You have requested a password reset. Please click the following link to reset your password:</p><p><a href="${resetUrl}">${resetUrl}</a></p>`,
          },
          Text: {
            Charset: "UTF-8",
            Data: `You have requested a password reset. Please click the following link to reset your password: ${resetUrl}`,
          },
        },
        Subject: {
          Charset: 'UTF-8',
          Data: 'Password Reset Request',
        },
      },
      Source: process.env.FROM_EMAIL,
    };

    await ses.sendEmail(params).promise();

    res.status(200).json({ message: 'Password reset email sent' });
  } catch (error) {
    console.error('Error sending email:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
}
