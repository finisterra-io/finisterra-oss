import sgMail from "@sendgrid/mail";
sgMail.setApiKey(process.env.SENDGRID_API_KEY);

export default async function sendContactEmail(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ message: "Method not allowed" });
  }
  // No need for session check here unless you want to restrict this functionality

  const { name, email, message } = req.body; // Adjust according to your form fields

  try {
    // Prepare the email message
    const msg = {
      to: "hello@finisterra.com",
      cc: "eng@finisterra.com",
      from: "daniel@finisterra.io",
      subject: "New Contact Form Submission",
      text: `You have received a new contact form submission from ${name} (${email}). Message: ${message}`,
      html: `<p>You have received a new contact form submission from <strong>${name} (${email})</strong>.</p><p>Message:</p><blockquote>${message}</blockquote>`,
    };

    // Send the email
    await sgMail.send(msg);

    console.log("Contact form email sent successfully");

    return res.status(200).json({ message: "Email sent successfully" });
  } catch (error) {
    console.error("Error sending contact form email:", error);
    return res.status(500).json({ message: "Error sending email" });
  }
}
