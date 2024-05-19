//prisma db seed
const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();

async function main() {
  const provider = await prisma.provider.upsert({
    where: { name: "AWS" },
    update: {},
    create: {
      name: "AWS",
      description: "AWS provider",
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "acm" },
    update: {},
    create: {
      code: "acm",
      name: "ACM (Certificate Manager)",
      description: "ACM (Certificate Manager)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "apigateway" },
    update: {},
    create: {
      code: "apigateway",
      name: "API Gateway",
      description: "API Gateway",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "apigatewayv2" },
  //   update: {},
  //   create: {
  //     code: "apigatewayv2",
  //     name: "API Gateway V2",
  //     description: "API Gateway V2",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "autoscaling" },
    update: {},
    create: {
      code: "autoscaling",
      name: "Auto Scaling",
      description: "Auto Scaling",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "backup" },
  //   update: {},
  //   create: {
  //     code: "backup",
  //     name: "Backup",
  //     description: "Backup",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "cloudmap" },
    update: {},
    create: {
      code: "cloudmap",
      name: "Cloud Map",
      description: "Cloud Map",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "cloudfront" },
    update: {},
    create: {
      code: "cloudfront",
      name: "CloudFront",
      description: "CloudFront",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "cloudtrail" },
  //   update: {},
  //   create: {
  //     code: "cloudtrail",
  //     name: "CloudTrail",
  //     description: "CloudTrail",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  // await prisma.providerGroup.upsert({
  //   where: { code: "cloudwatch" },
  //   update: {},
  //   create: {
  //     code: "cloudwatch",
  //     name: "CloudWatch",
  //     description: "CloudWatch",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "logs" },
    update: {},
    create: {
      code: "logs",
      name: "CloudWatch Logs",
      description: "CloudWatch Logs",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "cognito_idp" },
  //   update: {},
  //   create: {
  //     code: "cognito_idp",
  //     name: "Cognito IDP (Identity Provider)",
  //     description: "Cognito IDP (Identity Provider)",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  // await prisma.providerGroup.upsert({
  //   where: { code: "cognito_identity" },
  //   update: {},
  //   create: {
  //     code: "cognito_identity",
  //     name: "Cognito Identity",
  //     description: "Cognito Identity",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "docdb" },
    update: {},
    create: {
      code: "docdb",
      name: "DocDB (DocumentDB)",
      description: "DocDB (DocumentDB)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "dynamodb" },
    update: {},
    create: {
      code: "dynamodb",
      name: "DynamoDB",
      description: "DynamoDB",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "ebs" },
    update: {},
    create: {
      code: "ebs",
      name: "EBS (EC2)",
      description: "EBS (EC2)",
      active: false,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "ec2" },
    update: {},
    create: {
      code: "ec2",
      name: "EC2 (Elastic Compute Cloud)",
      description: "EC2 (Elastic Compute Cloud)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "ecr" },
    update: {},
    create: {
      code: "ecr",
      name: "ECR (Elastic Container Registry)",
      description: "ECR (Elastic Container Registry)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "ecr_public" },
  //   update: {},
  //   create: {
  //     code: "ecr_public",
  //     name: "ECR Public",
  //     description: "ECR Public",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "ecs" },
    update: {},
    create: {
      code: "ecs",
      name: "ECS (Elastic Container)",
      description: "ECS (Elastic Container)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "efs" },
  //   update: {},
  //   create: {
  //     code: "efs",
  //     name: "EFS (Elastic File System)",
  //     description: "EFS (Elastic File System)",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "eks" },
    update: {},
    create: {
      code: "eks",
      name: "EKS (Elastic Kubernetes)",
      description: "EKS (Elastic Kubernetes)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "elbv2" },
    update: {},
    create: {
      code: "elbv2",
      name: "ELB (Elastic Load Balancing)",
      description: "ELB (Elastic Load Balancing)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "elb" },
  //   update: {},
  //   create: {
  //     code: "elb",
  //     name: "ELB Classic",
  //     description: "ELB Classic",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  // await prisma.providerGroup.upsert({
  //   where: { code: "elasticache_memcached" },
  //   update: {},
  //   create: {
  //     code: "elasticache_memcached",
  //     name: "ElastiCacheMemcached",
  //     description: "ElastiCacheMemcached",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "elasticache_redis" },
    update: {},
    create: {
      code: "elasticache_redis",
      name: "ElastiCacheRedis",
      description: "ElastiCacheRedis",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "elasticbeanstalk" },
    update: {},
    create: {
      code: "elasticbeanstalk",
      name: "Elastic Beanstalk",
      description: "Elastic Beanstalk",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "es" },
    update: {},
    create: {
      code: "es",
      name: "Elasticsearch",
      description: "Elasticsearch",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "guardduty" },
  //   update: {},
  //   create: {
  //     code: "guardduty",
  //     name: "GuardDuty",
  //     description: "GuardDuty",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "iam" },
    update: {},
    create: {
      code: "iam",
      name: "IAM",
      description: "IAM",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "kms" },
    update: {},
    create: {
      code: "kms",
      name: "KMS (Key Management)",
      description: "KMS (Key Management)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "aws_lambda" },
    update: {},
    create: {
      code: "aws_lambda",
      name: "Lambda",
      description: "Lambda",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "opensearch" },
  //   update: {},
  //   create: {
  //     code: "opensearch",
  //     name: "OpenSearch",
  //     description: "OpenSearch",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "rds" },
    update: {},
    create: {
      code: "rds",
      name: "RDS (Relational Database)",
      description: "RDS (Relational Database)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "aurora" },
    update: {},
    create: {
      code: "aurora",
      name: "Aurora (Relational Database)",
      description: "Aurora (Relational Database)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "route53" },
  //   update: {},
  //   create: {
  //     code: "route53",
  //     name: "Route 53",
  //     description: "Route 53",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "s3" },
    update: {},
    create: {
      code: "s3",
      name: "S3 (Simple Storage)",
      description: "S3 (Simple Storage)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "sns" },
    update: {},
    create: {
      code: "sns",
      name: "SNS (Simple Notification)",
      description: "SNS (Simple Notification)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "sqs" },
    update: {},
    create: {
      code: "sqs",
      name: "SQS (Simple Queue)",
      description: "SQS (Simple Queue)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  // await prisma.providerGroup.upsert({
  //   where: { code: "ssm" },
  //   update: {},
  //   create: {
  //     code: "ssm",
  //     name: "SSM (Systems Manager)",
  //     description: "SSM (Systems Manager)",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  // await prisma.providerGroup.upsert({
  //   where: { code: "secretsmanager" },
  //   update: {},
  //   create: {
  //     code: "secretsmanager",
  //     name: "Secrets Manager",
  //     description: "Secrets Manager",
  //     active: false,
  //     provider: {
  //       connect: {
  //         id: provider.id,
  //       },
  //     },
  //   },
  // });

  await prisma.providerGroup.upsert({
    where: { code: "vpc" },
    update: {},
    create: {
      code: "vpc",
      name: "VPC (Virtual Private Cloud)",
      description: "VPC (Virtual Private Cloud)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "vpn_client" },
    update: {},
    create: {
      code: "vpn_client",
      name: "VPN (Client)",
      description: "VPN (Client)",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "wafv2" },
    update: {},
    create: {
      code: "wafv2",
      name: "WAF",
      description: "WAF",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "msk" },
    update: {},
    create: {
      code: "msk",
      name: "MSK",
      description: "MSK",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "security_group" },
    update: {},
    create: {
      code: "security_group",
      name: "Security Group",
      description: "Security Group",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });

  await prisma.providerGroup.upsert({
    where: { code: "stepfunction" },
    update: {},
    create: {
      code: "stepfunction",
      name: "Step Function",
      description: "Step Function",
      active: true,
      provider: {
        connect: {
          id: provider.id,
        },
      },
    },
  });
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
