// pages/api/auth/reset-password.js

import { PrismaClient } from '@prisma/client';
import sgMail from '@sendgrid/mail';

const prisma = new PrismaClient();

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

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

    const msg = {
      to: email,
    //   from: process.env.SENDGRID_FROM_EMAIL,
      from: "daniel@finisterra.io",
      subject: 'Password Reset Request',
      text: `You have requested a password reset. Please click the following link to reset your password: ${resetUrl}`,
      html: `<p>You have requested a password reset. Please click the following link to reset your password:</p><p><a href="${resetUrl}">${resetUrl}</a></p>`,
    };
    

    await sgMail.send(msg);

    res.status(200).json({ message: 'Password reset email sent' });
  } catch (error) {
    console.error('Error sending email:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
}
