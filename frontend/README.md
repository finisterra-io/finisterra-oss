# ft-fs Helm Chart Deployment Guide

This guide provides step-by-step instructions for deploying the ft-fs application using Helm on Kubernetes.

## Prerequisites

- Kubernetes cluster (version 1.14+)
- Helm 3.x installed
- kubectl configured to access your cluster
- Access to the ECR repository: `379070455575.dkr.ecr.us-east-1.amazonaws.com/ft-fs`

## Chart Overview

The ft-fs chart deploys a Next.js application with the following components:
- Deployment with configurable replicas
- Service (NodePort by default)
- Ingress (AWS ALB with SSL termination)
- ServiceAccount
- Horizontal Pod Autoscaler (optional)

## Required Secrets

Before deploying, you must create a Kubernetes secret named `ft-fs` with the following keys:

```bash
kubectl create secret generic ft-fs \
  --from-literal=AZURE_AD_CLIENT_SECRET="your-azure-ad-client-secret" \
  --from-literal=NEXTAUTH_SECRET_KEY="your-nextauth-secret-key" \
  --from-literal=JWT_SECRET="your-jwt-secret" \
  --from-literal=GITHUB_SECRET="your-github-secret" \
  --from-literal=DATABASE_URL="your-database-url" \
  --from-literal=SENDGRID_API_KEY="your-sendgrid-api-key" \
  --from-literal=GITHUB_WEBHOOK_SECRET="your-github-webhook-secret" \
  --from-literal=GITHUB_PR_SECRET="your-github-pr-secret" \
  --from-literal=GITHUB_APP_PEM="your-github-app-pem-content" \
  --from-literal=INTERNAL_API_KEY="your-internal-api-key" \
  --from-literal=STRIPE_SECRET_KEY="your-stripe-secret-key" \
  --from-literal=STRIPE_WEBHOOK_SECRET="your-stripe-webhook-secret"
```

## Environment Variables Configuration

Create a `values.yaml` file with your environment-specific configuration:

```yaml
# values.yaml
replicaCount: 2

image:
  repository: 379070455575.dkr.ecr.us-east-1.amazonaws.com/ft-fs
  pullPolicy: IfNotPresent
  sha: "your-image-sha-or-tag"

service:
  type: NodePort
  port: 3000

ingress:
  enabled: true  # Set to true to enable ingress
  className: "alb"
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: "internet-facing"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "your-certificate-arn"
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{"Type": "redirect", "RedirectConfig": { "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}'
  hosts:
    - host: your-domain.com
      paths:
        - path: /
          pathType: Prefix

# Environment variables (required)
env:
  NEXTAUTH_URL: "https://your-domain.com"
  GOOGLE_CLIENT_ID: "your-google-client-id"
  GOOGLE_CLIENT_SECRET: "your-google-client-secret"
  JWT_TIMEOUT: "3600"
  GITHUB_ID: "your-github-id"
  APP_URL: "https://your-domain.com"
  GITHUB_WEBHOOK_URL: "https://your-domain.com/api/github/webhook"
  GITHUB_APP_ID: "your-github-app-id"
  FT_BASE_URL: "https://your-ft-base-url"
  FT_API_HOST: "https://your-ft-api-host"
  STRIPE_PRICE_ID: "your-stripe-price-id"
  SENDGRID_FROM_EMAIL: "noreply@your-domain.com"
  AZURE_AD_CLIENT_ID: "your-azure-ad-client-id"
  AZURE_AD_TENANT_ID: "your-azure-ad-tenant-id"

# Optional: Resource limits
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

# Optional: Autoscaling
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
```

## Deployment Commands

### 1. Deploy the Chart

```bash
# Navigate to the chart directory
cd frontend/helm/charts/ft-fs

# Install the chart
helm install ft-fs . -f values.yaml

# Or upgrade if already installed
helm upgrade ft-fs . -f values.yaml
```

### 2. Alternative: Deploy with inline values

```bash
helm install ft-fs . \
  --set image.sha="your-image-sha" \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host="your-domain.com" \
  --set env.NEXTAUTH_URL="https://your-domain.com" \
  --set env.APP_URL="https://your-domain.com" \
  --set env.GOOGLE_CLIENT_ID="your-google-client-id" \
  --set env.GOOGLE_CLIENT_SECRET="your-google-client-secret" \
  # ... add other environment variables as needed
```

### 3. Deploy to a specific namespace

```bash
# Create namespace if it doesn't exist
kubectl create namespace ft-fs-prod

# Deploy to specific namespace
helm install ft-fs . -f values.yaml -n ft-fs-prod
```

## Verification

### Check deployment status
```bash
helm status ft-fs
kubectl get pods -l app.kubernetes.io/name=ft-fs
```

### Check logs
```bash
kubectl logs -l app.kubernetes.io/name=ft-fs --tail=100
```

### Access the application
```bash
# If using NodePort
kubectl get svc ft-fs
# Note the NodePort and access via http://<node-ip>:<node-port>

# If using Ingress
kubectl get ingress ft-fs
# Access via the configured host
```

## Environment Variables Reference

### Required Environment Variables (stored in values.yaml)
- `NEXTAUTH_URL`: NextAuth.js callback URL
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `JWT_TIMEOUT`: JWT token expiration time
- `GITHUB_ID`: GitHub OAuth app ID
- `APP_URL`: Application base URL
- `GITHUB_WEBHOOK_URL`: GitHub webhook endpoint
- `GITHUB_APP_ID`: GitHub App ID
- `FT_BASE_URL`: Finisterra base URL
- `FT_API_HOST`: Finisterra API host
- `STRIPE_PRICE_ID`: Stripe price ID for billing
- `SENDGRID_FROM_EMAIL`: SendGrid sender email
- `AZURE_AD_CLIENT_ID`: Azure AD client ID
- `AZURE_AD_TENANT_ID`: Azure AD tenant ID

### Required Secrets (stored in Kubernetes secret)
- `AZURE_AD_CLIENT_SECRET`: Azure AD client secret
- `NEXTAUTH_SECRET_KEY`: NextAuth.js secret key
- `JWT_SECRET`: JWT signing secret
- `GITHUB_SECRET`: GitHub OAuth secret
- `DATABASE_URL`: Database connection string
- `SENDGRID_API_KEY`: SendGrid API key
- `GITHUB_WEBHOOK_SECRET`: GitHub webhook secret
- `GITHUB_PR_SECRET`: GitHub PR secret
- `GITHUB_APP_PEM`: GitHub App private key (PEM format)
- `INTERNAL_API_KEY`: Internal API authentication key
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret

## Troubleshooting

### Common Issues

1. **Image pull errors**: Ensure you have access to the ECR repository and correct credentials
2. **Secret not found**: Verify the `ft-fs` secret exists in the same namespace
3. **Environment variable issues**: Check that all required environment variables are set in values.yaml
4. **Ingress not working**: Ensure AWS Load Balancer Controller is installed and configured

### Useful Commands

```bash
# Get all resources
kubectl get all -l app.kubernetes.io/name=ft-fs

# Describe pod for detailed information
kubectl describe pod -l app.kubernetes.io/name=ft-fs

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Port forward for local testing
kubectl port-forward svc/ft-fs 3000:3000
```

## Uninstallation

```bash
# Uninstall the chart
helm uninstall ft-fs

# Clean up secrets (if needed)
kubectl delete secret ft-fs
```

## Security Considerations

- Store sensitive values in Kubernetes secrets, not in values.yaml
- Use RBAC to restrict access to secrets
- Consider using external secret management solutions like AWS Secrets Manager
- Regularly rotate secrets and API keys
- Use network policies to restrict pod-to-pod communication if needed 
