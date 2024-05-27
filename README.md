# Finisterra

Finisterra is a tool for helping engineers create Terraform code for existing resources in different clouds. This helps teams that do not have Terraform code for their infrastructure, or that have a lot of drifts in their infrastructure and want to start from scratch, to have a way to create Terraform code based on the existing resources.

The Terraform code generated follows the best practices:

- Use of [Terraform modules](https://github.com/orgs/finisterra-io/repositories).
- Use of remote state.
- Use of variables or references to other modules instead of hardcoding IDs.
- Filesystem structure to support different providers, accounts, regions, services, etc., in the same repository.
- Small state files following the structure as in the filesystem to avoid bloated states.
- Code is formatted.
- Code is validated.
- Checkov is executed on the generated code.

Finisterra does not receive or use any of your cloud credentials. Every request to the cloud API is executed within your workstation or within your GitHub organization using an OIDC role.


## Table of Contents

- [Quickstart](#quickstart)
- [Use Cases](#use-cases)
- [Demo](#demo)
- [Supported Modules](#supported-modules)
- [Docs](#docs)
- [Contributing](#contributing)

## Quickstart

### Finisterra Cloud (Recommended)

Using Finisterra Cloud, you get unlimited free code generation in one cloud account in one region.

```bash
pip install finisterra
```

For example, to generate the code for all the S3 buckets and SNS topics, and store the code in /tmp/code, just run the following:

```
finisterra -p aws -m "s3,sns" -o /tmp/code
```

### Open-source hobby deploy (Advanced)

You can deploy a hobby version of Finisterra in your workstation, with one command:

```bash
 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/finisterra-io/finisterra/HEAD/bin/hobby-deploy.sh)" 
```

## Use Cases

- **Reverse Terraform:** Create Terraform code for existing infrastructure.
- **Stacks:** You can filter by tags and group different resources to create stacks. For instance, you can create stacks per environment like dev, staging, and prod. Or you can create stacks by applications, for example billing, marketing, etc.
- **Drift Detection and Fix:** Finisterra is scheduled to run so every time there is a manual configuration, it is detected and a pull request is created to automatically update the Terraform code and state to keep it in sync.
- **CICD:** Finisterra pushes a CICD workflow to your repository so you can keep managing your infrastructure from the generated code. If you open a pull request, the workflow is triggered and posts the Terraform plan to your pull request as a comment. Once the pull request is approved and merged, the workflow triggers a Terraform apply.
- **Disaster Recovery:** Finisterra can be used to create a backup of your infrastructure in a different region or account. Or in case of a disaster, you can use the generated code to recreate your infrastructure.
- **Infrastructure Documentation:** The code can serve as documentation of the infrastructure.
- **Cost Savings:** By having all the code centralized, you can easily identify resources that are not being used and delete them.
- **Audit of Infra Changes:** Because Finisterra runs as a scheduled job, it detects any manual changes in the infrastructure and creates a pull request to keep the code in sync with the infrastructure. This way, you can audit who made the changes and why.

## Demo

### Using the webapp

[Video](https://www.youtube.com/watch?v=-sIYBNtSMug)

### Using the CLI

[Video](https://www.youtube.com/watch?v=HHsAL_5nfKY)

## Supported Modules

[Modules](https://finisterra.io/docs/providers/aws)

## Docs

[Docs](https://finisterra.io/docs/quickstart/web)

## Contributing

Contributions are welcome! If you have suggestions for improving Finisterra or adding new features, please feel free to submit a pull request or create an issue.

