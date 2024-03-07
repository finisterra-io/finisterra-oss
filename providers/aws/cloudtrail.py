import os
from utils.hcl import HCL
from botocore.exceptions import ClientError


class Cloudtrail:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def cloudtrail(self):
        self.hcl.prepare_folder(os.path.join("generated", "cloudtrail"))

        self.aws_cloudtrail()  # Import fails
        self.aws_cloudtrail_event_data_store()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_cloudtrail(self):
        print("Processing AWS CloudTrail...")

        trails = self.aws_clients.cloudtrail_client.describe_trails()["trailList"]
        for trail in trails:
            trail_arn = trail["TrailARN"]
            trail_name = trail["Name"]
            trail_region = trail["HomeRegion"]

            # Ignore the trail if it's not in the specified region
            if trail_region != self.region:
                continue

            print(f"Processing AWS CloudTrail: {trail_name}")

            attributes = {
                "id": trail_name,
                "arn": trail_arn,
                "name": trail_name,
                "s3_bucket_name": trail["S3BucketName"],
                "s3_key_prefix": trail.get("S3KeyPrefix", ""),
                "cloud_watch_logs_role_arn": trail.get("CloudWatchLogsRoleArn", ""),
                "cloud_watch_logs_group_arn": trail.get("CloudWatchLogsLogGroupArn", ""),
                "sns_topic_name": trail.get("SnsTopicName", ""),
            }

            self.hcl.process_resource(
                "aws_cloudtrail", trail_name.replace("-", "_"), attributes)

    def aws_cloudtrail_event_data_store(self):
        print("Processing AWS CloudTrail Event Data Store...")

        trails = self.aws_clients.cloudtrail_client.describe_trails()["trailList"]

        for trail in trails:
            trail_name = trail["Name"]
            trail_arn = trail["TrailARN"]

            try:
                response = self.aws_clients.cloudtrail_client.get_event_selectors(
                    TrailName=trail_name)
                event_selectors = response["EventSelectors"]

                for event_selector in event_selectors:
                    for data_resource in event_selector["DataResources"]:
                        if data_resource["Type"] == "AWS::S3::Object":
                            print(
                                f"Processing AWS CloudTrail Event Data Store: {data_resource['Values'][0]}")

                            attributes = {
                                "id": data_resource["Values"][0],
                                "trail_arn": trail_arn,
                                "type": data_resource["Type"],
                                "values": data_resource["Values"],
                            }

                            self.hcl.process_resource(
                                "aws_cloudtrail_event_data_store", data_resource["Values"][0].replace("/", "_"), attributes)
            except ClientError as e:
                if e.response['Error']['Code'] == 'TrailNotFoundException':
                    print(f"  Trail not found: {trail_arn}")
                else:
                    raise
