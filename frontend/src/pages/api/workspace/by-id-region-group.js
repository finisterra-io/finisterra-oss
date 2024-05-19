import { PrismaClient } from "@prisma/client";
import { getServerSession } from "next-auth/next";
import { authOptions } from "pages/api/auth/[...nextauth]";

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

    // Handling POST requests for Workspace creation
    if (req.method === 'POST') {
        const { name, account_id, provider_name, provider_group_code, region } = req.body;
        
        // Validate the input parameters
        if (!name || !account_id || !provider_name || !provider_group_code || !region) {
            return res.status(400).json({ message: "Bad Request: All fields are required." });
        }
        
        try {
            // Find ProviderGroup based on code
            const providerGroup = await prisma.providerGroup.findUnique({
                where: {
                    code: provider_group_code
                }
            });

            if (!providerGroup) {
                return res.status(404).json({ message: "Provider group not found" });
            }

            // Check if the Workspace already exists
            const existingWorkspace = await prisma.workspace.findFirst({
                where: {
                    awsAccountId: parseInt(account_id),
                    providerGroupId: providerGroup.id,
                    awsRegion: region,
                    organizationId: organizationId
                }
            });

            if (existingWorkspace) {
                return res.status(409).json({ message: "Workspace already exists.", id: existingWorkspace.id });
            }

            // Create a new Workspace if not exists
            const newWorkspace = await prisma.workspace.create({
                data: {
                    name: name,
                    organizationId: organizationId,
                    awsAccountId: parseInt(account_id),
                    providerGroupId: providerGroup.id,
                    awsRegion: region,
                    enabled: true
                }
            });
            
            return res.status(201).json(newWorkspace);
        } catch (error) {
            console.error("Error creating Workspace:", error);
            return res.status(500).json({ error: "Failed to create Workspace" });
        }
    } else {
        // Method not allowed
        return res.status(405).json({ message: "Method Not Allowed" });
    }
}
