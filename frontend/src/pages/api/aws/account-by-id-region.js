    import { PrismaClient } from "@prisma/client";
    import { getServerSession } from "next-auth/next";
    import { authOptions } from "pages/api/auth/[...nextauth]";
    import { updateSubscription } from "utils/billing/subscription";

    const prisma = new PrismaClient();

    export default async function handle(req, res) {
        const authHeader = req.headers["authorization"];
        const apiKey = authHeader && authHeader.split(" ")[1];
        
        let validKey;
        if (apiKey) {
            validKey = await prisma.apiKey.findUnique({
                where: { key: apiKey },
            });
        }
        
        const session = await getServerSession(req, res, authOptions);
        
        if (!session && !validKey) {
            return res.status(401).json({ message: "Unauthorized" });
        }
        
        let organizationId;
        if (session) {
            organizationId = session.organizationId;
        } else {
            organizationId = validKey.organizationId;
        }
        
        // Handling GET requests
        if (req.method === 'GET') {
            const { account_id, region } = req.query;
            
            // Validate the parameters
            if (!account_id || !region) {
                return res.status(400).json({ message: "Bad Request: Both account_id and region are required." });
            }
            
            try {
                const awsAccountDetails = await prisma.awsAccount.findMany({
                    where: {
                        awsAccountId: account_id,
                        region: region,
                    }
                });
                
                if (!awsAccountDetails || awsAccountDetails.length === 0) {
                    return res.status(404).json({ message: "AwsAccount not found" });
                }
                
                return res.json(awsAccountDetails);
            } catch (error) {
                console.error("Error retrieving AWS account details:", error);
                return res.status(500).json({ error: "Failed to retrieve AWS account details" });
            }
        }
        // Handling POST requests
        else if (req.method === 'POST') {
            const { account_id, region, name, role_arn } = req.body;
            
            // Validate the input parameters
            if (!account_id || !region) {
                return res.status(400).json({ message: "Bad Request: Both awsAccountId and region are required." });
            }
            
            try {
                // Check if the AWS account already exists
                const existingAccount = await prisma.awsAccount.findFirst({
                    where: {
                        awsAccountId: account_id,
                        region: region
                    }
                });
                
                if (existingAccount) {
                    return res.status(409).json({ message: "AWS Account already exists.", id: existingAccount.id });
                }
                
                // Create a new AWS Account if not exists
                const newAwsAccount = await prisma.awsAccount.create({
                    data: {
                        name: name || account_id,
                        awsAccountId: account_id,
                        region,
                        organizationId: organizationId,
                        roleArn: role_arn || `arn:aws:iam::${account_id}:role/ft-ro-gha-cicd-role`, 
                        enabled: true,
                    }
                });
                updateSubscription({ organizationId });
                
                return res.status(201).json(newAwsAccount);
            } catch (error) {
                console.error("Error creating AWS account:", error);
                return res.status(500).json({ error: "Failed to create AWS account" });
            }
        } else {
            // Method not allowed
            return res.status(405).json({ message: "Method Not Allowed" });
        }
    }
