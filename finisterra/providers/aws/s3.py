from ...utils.hcl import HCL
from botocore.exceptions import ClientError
from botocore.exceptions import ClientError
from ...providers.aws.iam_role import IAM
import logging
import inspect

logger = logging.getLogger('finisterra')


class S3:
    def __init__(self, provider_instance, hcl=None):
        self.provider_instance = provider_instance
        if not hcl:
            self.hcl = HCL(self.provider_instance.schema_data)
        else:
            self.hcl = hcl

        self.hcl.region = self.provider_instance.region
        self.hcl.output_dir = self.provider_instance.output_dir
        self.hcl.account_id = self.provider_instance.aws_account_id

        self.hcl.provider_name = self.provider_instance.provider_name
        self.hcl.provider_name_short = self.provider_instance.provider_name_short
        self.hcl.provider_source = self.provider_instance.provider_source
        self.hcl.provider_version = self.provider_instance.provider_version
        self.hcl.account_name = self.provider_instance.account_name

        self.iam_role_instance = IAM(self.provider_instance, self.hcl)

    def s3(self):
        self.hcl.prepare_folder()
        self.aws_s3_bucket()
        self.hcl.module = inspect.currentframe().f_code.co_name
        if self.hcl.count_state():
            self.provider_instance.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.provider_instance.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            if self.hcl.request_tf_code():
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[green]{self.__class__.__name__} [bold]Code Generated[/]")
            else:
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[orange3]{self.__class__.__name__} [bold]No code generated[/]")
        else:
            self.task = self.provider_instance.progress.add_task(
                f"[orange3]{self.__class__.__name__} [bold]No resources found[/]", total=1)
            self.provider_instance.progress.update(self.task, advance=1)

    def aws_s3_bucket(self, selected_s3_bucket=None, ftstack=None):
        resource_name = "aws_s3_bucket"

        if selected_s3_bucket and ftstack:
            if self.hcl.id_resource_processed(resource_name, selected_s3_bucket, ftstack):
                # logger.debug(f"Skipping S3 Bucket: {selected_s3_bucket} - already processed")
                return
            try:
                self.process_single_s3_bucket(selected_s3_bucket, ftstack)
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDenied':
                    # logger.error(f"Access Denied: {e.response['Error']['Message']}")
                    pass
                else:
                    raise e
            return

        response = self.provider_instance.aws_clients.s3_client.list_buckets()
        all_buckets = response["Buckets"]

        filtered_buckets = []
        for bucket in all_buckets:
            bucket_name = bucket["Name"]
            try:
                # Attempt to fetch tags for each bucket
                tag_set = self.provider_instance.aws_clients.s3_client.get_bucket_tagging(
                    Bucket=bucket_name)['TagSet']
                bucket_tags = {tag['Key']: tag['Value'] for tag in tag_set}
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchTagSet':
                    bucket_tags = {}
                elif e.response['Error']['Code'] in ['AccessDenied', 'NoSuchBucket']:
                    # Skip buckets that cannot be accessed or don't exist
                    continue
                else:
                    raise e  # Re-raise if it's a different kind of error

            # Check if bucket matches all filter conditions
            match_all_conditions = all(
                any(bucket_tags.get(f['Name'].replace(
                    'tag:', ''), '') == value for value in f['Values'])
                for f in self.provider_instance.filters
            ) if self.provider_instance.filters else True

            if match_all_conditions:
                filtered_buckets.append(bucket)

        if len(filtered_buckets) > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(filtered_buckets))

        for bucket in filtered_buckets:
            bucket_name = bucket["Name"]
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{bucket_name}[/]")

            try:
                bucket_location_response = self.provider_instance.aws_clients.s3_client.get_bucket_location(
                    Bucket=bucket_name)
                bucket_region = bucket_location_response.get(
                    'LocationConstraint', 'us-east-1') or 'us-east-1'

                if bucket_region == self.provider_instance.region:
                    self.process_single_s3_bucket(bucket_name, ftstack)
            except ClientError as e:
                logger.error(
                    f"Access Denied: {e.response['Error']['Message']}")
                pass

    def process_single_s3_bucket(self, bucket_name, ftstack=None):
        logger.debug(f"Processing S3 Bucket: {bucket_name}")
        resource_type = "aws_s3_bucket"

        # if bucket_name != "xxxx":
        #     return

        # Retrieve the region of the bucket
        bucket_location_response = self.provider_instance.aws_clients.s3_client.get_bucket_location(
            Bucket=bucket_name)
        bucket_region = bucket_location_response['LocationConstraint']

        # If bucket_region is None, set it to us-east-1
        if bucket_region is None:
            bucket_region = 'us-east-1'

        # Skip processing if the bucket's region does not match self.provider_instance.region
        if bucket_region != self.provider_instance.region:
            logger.debug(
                f"  Skipping S3 Bucket (different region): {bucket_name}")
            return

        # Describe the bucket and get the tags
        if not ftstack:
            ftstack = "s3"
            try:
                response = self.provider_instance.aws_clients.s3_client.get_bucket_tagging(
                    Bucket=bucket_name)
                tags = response.get('TagSet', {})
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 's3':
                            ftstack = "stack_" + tag['Value']
                        break
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchTagSet':
                    pass
                else:
                    raise e

        id = bucket_name

        attributes = {
            "id": id,
            "bucket": bucket_name,
        }

        self.hcl.process_resource(resource_type, bucket_name, attributes)
        self.hcl.add_stack(resource_type, id, ftstack)

        # Add calls to various aws_s3_bucket_* functions
        if "gov" not in self.provider_instance.region:
            self.aws_s3_bucket_accelerate_configuration(bucket_name)
            self.aws_s3_bucket_intelligent_tiering_configuration(bucket_name)

        self.aws_s3_bucket_acl(bucket_name)
        self.aws_s3_bucket_analytics_configuration(bucket_name)
        self.aws_s3_bucket_cors_configuration(bucket_name)
        self.aws_s3_bucket_inventory(bucket_name)
        self.aws_s3_bucket_lifecycle_configuration(bucket_name)
        self.aws_s3_bucket_logging(bucket_name)
        self.aws_s3_bucket_metric(bucket_name)
        # self.aws_s3_bucket_notification(bucket_name) #will be called from other modules
        self.aws_s3_bucket_object_lock_configuration(bucket_name)
        self.aws_s3_bucket_ownership_controls(bucket_name)
        self.aws_s3_bucket_policy(bucket_name)
        self.aws_s3_bucket_public_access_block(bucket_name)
        self.aws_s3_bucket_replication_configuration(bucket_name)
        self.aws_s3_bucket_request_payment_configuration(bucket_name)
        self.aws_s3_bucket_server_side_encryption_configuration(bucket_name)
        self.aws_s3_bucket_versioning(bucket_name)
        self.aws_s3_bucket_website_configuration(bucket_name)

    def aws_s3_bucket_accelerate_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Accelerate Configurations...")

        try:
            accelerate_config = self.provider_instance.aws_clients.s3_client.get_bucket_accelerate_configuration(
                Bucket=bucket_name)
            status = accelerate_config.get("Status", None)
            if status:
                logger.debug(
                    f"Processing S3 Bucket Accelerate Configuration: {bucket_name}")

                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "accelerate_status": status,
                }

                self.hcl.process_resource(
                    "aws_s3_bucket_accelerate_configuration", bucket_name, attributes)
            else:
                logger.debug(
                    f"  No Accelerate Configuration found for S3 Bucket: {bucket_name}")
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchAccelerateConfiguration":
                logger.debug(
                    f"  No Accelerate Configuration found for S3 Bucket: {bucket_name}")
            else:
                raise

    def aws_s3_bucket_acl(self, bucket_name):
        logger.debug(f"Processing S3 Bucket ACLs...")

        # Get the Canonical User ID of your AWS account
        account_canonical_id = self.provider_instance.aws_clients.s3_client.list_buckets()[
            'Owner']['ID']

        # Try to get the object ownership control of the bucket
        try:
            ownership_controls = self.provider_instance.aws_clients.s3_client.get_bucket_ownership_controls(
                Bucket=bucket_name)
            object_ownership = ownership_controls['OwnershipControls']['Rules'][0]['ObjectOwnership']
        except ClientError as e:
            if e.response['Error']['Code'] == 'OwnershipControlsNotFoundError':
                # If the bucket does not have ownership controls, skip it and continue with the next bucket
                logger.debug(
                    f"  Skipping S3 Bucket: {bucket_name} - No ownership controls found.")
                return
            else:
                # If some other error occurred, re-raise the exception
                raise

        acl = self.provider_instance.aws_clients.s3_client.get_bucket_acl(
            Bucket=bucket_name)

        # Check if the bucket's owner is someone external
        bucket_owner_canonical_id = acl['Owner']['ID']

        # Only process the ACL if bucket's owner is someone external
        # and object_ownership is not BucketOwnerEnforced
        if bucket_owner_canonical_id != account_canonical_id and object_ownership != 'BucketOwnerEnforced':
            logger.debug(f"Processing S3 Bucket ACL: {bucket_name}")

            attributes = {
                "id": bucket_name,
                "bucket": bucket_name,
                # "acl": acl["Grants"],
            }
            self.hcl.process_resource(
                "aws_s3_bucket_acl", bucket_name, attributes)

    def aws_s3_bucket_analytics_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Analytics Configurations...")

        analytics_configs = self.provider_instance.aws_clients.s3_client.list_bucket_analytics_configurations(
            Bucket=bucket_name)

        if "AnalyticsConfigurationList" not in analytics_configs:
            return

        for config in analytics_configs["AnalyticsConfigurationList"]:
            config_id = config["Id"]
            logger.debug(
                f"Processing S3 Bucket Analytics Configuration: {config_id} for bucket {bucket_name}")

            attributes = {
                "id": bucket_name+":"+config_id,
                # "bucket": bucket_name,
                # "name": config_id,
                # "filter": config["Filter"],
                # "storage_class_analysis": config["StorageClassAnalysis"],
            }
            self.hcl.process_resource(
                "aws_s3_bucket_analytics_configuration", f"{bucket_name}-{config_id}".replace(
                    "-", "_"),
                attributes
            )

    def aws_s3_bucket_cors_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket CORS Configurations...")

        try:
            cors = self.provider_instance.aws_clients.s3_client.get_bucket_cors(
                Bucket=bucket_name)
            logger.debug(
                f"Processing S3 Bucket CORS Configuration: {bucket_name}")

            attributes = {
                "id": bucket_name,
                "bucket": bucket_name,
                "rule": cors["CORSRules"],
            }
            self.hcl.process_resource(
                "aws_s3_bucket_cors_configuration", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchCORSConfiguration":
                logger.debug(
                    f"  No CORS Configuration for bucket: {bucket_name}")
            else:
                raise

    def aws_s3_bucket_intelligent_tiering_configuration(self, bucket_name):
        logger.debug(
            f"Processing S3 Bucket Intelligent Tiering Configurations...")

        intelligent_tiering_configs = self.provider_instance.aws_clients.s3_client.list_bucket_intelligent_tiering_configurations(
            Bucket=bucket_name)

        if "IntelligentTieringConfigurationList" not in intelligent_tiering_configs:
            return

        for config in intelligent_tiering_configs["IntelligentTieringConfigurationList"]:
            config_id = config["Id"]
            logger.debug(
                f"Processing S3 Bucket Intelligent Tiering Configuration: {config_id} for bucket {bucket_name}")

            attributes = {
                "id": bucket_name+":"+config_id,
                "bucket": bucket_name,
                "name": config_id,
                # "filter": config["Filter"],
                # "status": config["Status"],
                # "tierings": config["Tierings"],
            }
            self.hcl.process_resource("aws_s3_bucket_intelligent_tiering_configuration",
                                      f"{bucket_name}-{config_id}".replace("-", "_"), attributes)

    def aws_s3_bucket_inventory(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Inventories...")

        inventory_configs = self.provider_instance.aws_clients.s3_client.list_bucket_inventory_configurations(
            Bucket=bucket_name)

        if "InventoryConfigurationList" not in inventory_configs:
            return

        for config in inventory_configs["InventoryConfigurationList"]:
            config_id = config["Id"]
            logger.debug(
                f"Processing S3 Bucket Inventory: {config_id} for bucket {bucket_name}")

            attributes = {
                "id": bucket_name+":"+config_id,
                "bucket": bucket_name,
                # "name": config_id,
                # "destination": config["Destination"],
                # "schedule": config["Schedule"],
                # "included_object_versions": config["IncludedObjectVersions"],
                # "optional_fields": config["OptionalFields"] if "OptionalFields" in config else [],
                # "filter": config["Filter"] if "Filter" in config else None,
            }
            self.hcl.process_resource(
                "aws_s3_bucket_inventory", f"{bucket_name}-{config_id}".replace("-", "_"), attributes)

    def aws_s3_bucket_lifecycle_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Lifecycle Configurations...")
        try:
            lifecycle = self.provider_instance.aws_clients.s3_client.get_bucket_lifecycle_configuration(
                Bucket=bucket_name)
            logger.debug(
                f"Processing S3 Bucket Lifecycle Configuration: {bucket_name}")
            attributes = {
                "id": bucket_name,
                "bucket": bucket_name,
                "rule": lifecycle["Rules"],
            }
            self.hcl.process_resource(
                "aws_s3_bucket_lifecycle_configuration", bucket_name, attributes)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                logger.debug(
                    f"  No Lifecycle Configuration for bucket: {bucket_name}")
            else:
                raise

    def aws_s3_bucket_logging(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Logging...")
        logging = self.provider_instance.aws_clients.s3_client.get_bucket_logging(
            Bucket=bucket_name)
        if "LoggingEnabled" in logging:
            target_bucket = logging["LoggingEnabled"]["TargetBucket"]
            target_prefix = logging["LoggingEnabled"]["TargetPrefix"]
            logger.debug(f"Processing S3 Bucket Logging: {bucket_name}")
            attributes = {
                "id": bucket_name,
                "bucket": bucket_name,
                "target_bucket": target_bucket,
                "target_prefix": target_prefix,
            }
            self.hcl.process_resource(
                "aws_s3_bucket_logging", bucket_name, attributes)

    def aws_s3_bucket_metric(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Metrics...")
        metrics = self.provider_instance.aws_clients.s3_client.list_bucket_metrics_configurations(
            Bucket=bucket_name)
        if "MetricsConfigurationList" not in metrics:
            return
        for metric in metrics["MetricsConfigurationList"]:
            metric_id = metric["Id"]
            logger.debug(
                f"Processing S3 Bucket Metric: {metric_id} for bucket {bucket_name}")
            attributes = {
                "id": metric_id,
                "bucket": bucket_name,
                "name": metric_id,
                "filter": metric["Filter"] if "Filter" in metric else None,
            }
            self.hcl.process_resource(
                "aws_s3_bucket_metric", f"{bucket_name}-{metric_id}".replace("-", "_"), attributes)

    def aws_s3_bucket_notification(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Notifications...")
        notifications = self.provider_instance.aws_clients.s3_client.get_bucket_notification_configuration(
            Bucket=bucket_name)
        for event in notifications.keys():
            if event != "ResponseMetadata":
                logger.debug(
                    f"Processing S3 Bucket Notification: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "notification_configuration": {event: notifications[event]},
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_notification", bucket_name, attributes)

    def aws_s3_bucket_object(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Objects...")
        objects = self.provider_instance.aws_clients.s3_client.list_objects(
            Bucket=bucket_name)
        for obj in objects.get("Contents", []):
            key = obj["Key"]
            logger.debug(
                f"Processing S3 Bucket Object: {key} in bucket {bucket_name}")
            attributes = {
                "id": f"{bucket_name}/{key}",
                "bucket": bucket_name,
                "key": key,
            }
            self.hcl.process_resource(
                "aws_s3_bucket_object", f"{bucket_name}-{key}".replace("-", "_"), attributes)

    def aws_s3_bucket_object_lock_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Object Lock Configurations...")
        try:
            object_lock_configuration = self.provider_instance.aws_clients.s3_client.get_object_lock_configuration(
                Bucket=bucket_name)
            config = object_lock_configuration.get(
                "ObjectLockConfiguration", {})
            if config:
                logger.debug(
                    f"Processing S3 Bucket Object Lock Configuration: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "object_lock_configuration": config,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_object_lock_configuration", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ObjectLockConfigurationNotFoundError":
                raise
            else:
                logger.debug(
                    f"  No Object Lock Configuration for bucket: {bucket_name}")

    def aws_s3_bucket_ownership_controls(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Ownership Controls...")
        try:
            ownership_controls = self.provider_instance.aws_clients.s3_client.get_bucket_ownership_controls(
                Bucket=bucket_name)
            controls = ownership_controls.get("OwnershipControls", {})
            if controls:
                logger.debug(
                    f"Processing S3 Bucket Ownership Controls: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "ownership_controls": controls,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_ownership_controls", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "OwnershipControlsNotFoundError":
                raise
            else:
                logger.debug(
                    f"  No Ownership Controls for bucket: {bucket_name}")

    def aws_s3_bucket_policy(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Policies...")
        try:
            bucket_policy = self.provider_instance.aws_clients.s3_client.get_bucket_policy(
                Bucket=bucket_name)
            policy = bucket_policy.get("Policy")
            if policy:
                logger.debug(f"Processing S3 Bucket Policy: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "policy": policy,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_policy", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchBucketPolicy":
                raise

    def aws_s3_bucket_public_access_block(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Public Access Blocks...")
        try:
            public_access_block = self.provider_instance.aws_clients.s3_client.get_public_access_block(
                Bucket=bucket_name)
            block_config = public_access_block.get(
                "PublicAccessBlockConfiguration", {})
            if block_config:
                logger.debug(
                    f"Processing S3 Bucket Public Access Block: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "block_public_acls": block_config["BlockPublicAcls"],
                    "block_public_policy": block_config["BlockPublicPolicy"],
                    "ignore_public_acls": block_config["IgnorePublicAcls"],
                    "restrict_public_buckets": block_config["RestrictPublicBuckets"],
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_public_access_block", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchPublicAccessBlockConfiguration":
                raise

    def aws_s3_bucket_replication_configuration(self, bucket_name, ftstack=None):
        logger.debug(f"Processing S3 Bucket Replication Configurations...")
        try:
            if not ftstack:
                ftstack = 's3'
            replication_configuration = self.provider_instance.aws_clients.s3_client.get_bucket_replication(
                Bucket=bucket_name)
            config = replication_configuration.get(
                "ReplicationConfiguration")
            if config:
                logger.debug(
                    f"Processing S3 Bucket Replication Configuration: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "replication_configuration": config,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_replication_configuration", bucket_name, attributes)

                role = config.get("Role")
                if role:
                    role_name = role.split("/")[-1]
                    self.iam_role_instance.aws_iam_role(role_name, ftstack)

        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ReplicationConfigurationNotFoundError":
                raise

    def aws_s3_bucket_request_payment_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Request Payment Configurations...")
        try:
            request_payment_configuration = self.provider_instance.aws_clients.s3_client.get_bucket_request_payment(
                Bucket=bucket_name)
            config = request_payment_configuration.get("Payer")
            if config:
                logger.debug(
                    f"Processing S3 Bucket Request Payment Configuration: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "payer": config,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_request_payment_configuration", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchRequestPaymentConfiguration":
                raise

    def aws_s3_bucket_server_side_encryption_configuration(self, bucket_name):
        logger.debug(
            f"Processing S3 Bucket Server Side Encryption Configurations...")
        try:
            encryption_configuration = self.provider_instance.aws_clients.s3_client.get_bucket_encryption(
                Bucket=bucket_name)
            config = encryption_configuration.get(
                "ServerSideEncryptionConfiguration")
            if config:
                logger.debug(
                    f"Processing S3 Bucket Server Side Encryption Configuration: {bucket_name}")
                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "server_side_encryption_configuration": config,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_server_side_encryption_configuration", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ServerSideEncryptionConfigurationNotFoundError":
                raise

    def aws_s3_bucket_versioning(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Versioning Configurations...")

        try:
            versioning_configuration = self.provider_instance.aws_clients.s3_client.get_bucket_versioning(
                Bucket=bucket_name)
            config = versioning_configuration.get("Status")

            if config:
                logger.debug(
                    f"Processing S3 Bucket Versioning Configuration: {bucket_name}")

                attributes = {
                    "id": bucket_name,
                    "bucket": bucket_name,
                    "status": config,
                }
                self.hcl.process_resource(
                    "aws_s3_bucket_versioning", bucket_name, attributes)
        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchVersioningConfiguration":
                raise

    def aws_s3_bucket_website_configuration(self, bucket_name):
        logger.debug(f"Processing S3 Bucket Website Configurations...")

        try:
            website_config = self.provider_instance.aws_clients.s3_client.get_bucket_website(
                Bucket=bucket_name)
            logger.debug(
                f"Processing S3 Bucket Website Configuration: {bucket_name}")

            attributes = {
                "id": bucket_name,
            }
            self.hcl.process_resource(
                "aws_s3_bucket_website_configuration", bucket_name, attributes)

        except self.provider_instance.aws_clients.s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchWebsiteConfiguration":
                pass
                logger.debug(
                    f"  No website configuration found for bucket: {bucket_name}")
            else:
                raise
