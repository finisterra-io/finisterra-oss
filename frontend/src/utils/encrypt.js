import crypto from "crypto";

export const encrypt = async (plainText) => {
  const secretKey = process.env.GITHUB_PR_SECRET;
  // Hash the secret key
  const hashedKey = crypto
    .createHash("sha256")
    .update(String(secretKey))
    .digest();

  // Ensure the key length is 32 bytes
  if (hashedKey.length !== 32) {
    throw new Error("Invalid key length");
  }

  // Create an AES cipher using the hashed key
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv("aes-256-cbc", hashedKey, iv);
  let encrypted = cipher.update(String(plainText), "utf8", "base64");
  encrypted += cipher.final("base64");
  return `${iv.toString("base64")}:${encrypted}`;
};
