import os
from utils.hcl import HCL


class Cloudwatch:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def cloudwatch(self):
        self.hcl.prepare_folder(os.path.join("generated", "cloudwatch"))

        self.aws_cloudwatch_composite_alarm()
        self.aws_cloudwatch_dashboard()
        self.aws_cloudwatch_metric_alarm()
        if "gov" not in self.region:
            self.aws_cloudwatch_metric_stream()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_cloudwatch_composite_alarm(self):
        print("Processing CloudWatch Composite Alarms...")

        paginator = self.aws_clients.cloudwatch_client.get_paginator("describe_alarms")
        for page in paginator.paginate(AlarmTypes=["CompositeAlarm"]):
            for composite_alarm in page["CompositeAlarms"]:
                alarm_name = composite_alarm["AlarmName"]
                print(f"Processing CloudWatch Composite Alarm: {alarm_name}")

                attributes = {
                    "id": alarm_name,
                    "alarm_name": alarm_name,
                    "alarm_description": composite_alarm.get("AlarmDescription", ""),
                    "alarm_rule": composite_alarm["AlarmRule"],
                    "actions_enabled": composite_alarm["ActionsEnabled"],
                    "alarm_actions": composite_alarm.get("AlarmActions", []),
                    "insufficient_data_actions": composite_alarm.get("InsufficientDataActions", []),
                    "ok_actions": composite_alarm.get("OKActions", []),
                }

                self.hcl.process_resource(
                    "aws_cloudwatch_composite_alarm", alarm_name.replace("-", "_"), attributes)

    def aws_cloudwatch_dashboard(self):
        print("Processing CloudWatch Dashboards...")

        paginator = self.aws_clients.cloudwatch_client.get_paginator("list_dashboards")
        for page in paginator.paginate():
            for dashboard in page["DashboardEntries"]:
                dashboard_name = dashboard["DashboardName"]
                print(f"Processing CloudWatch Dashboard: {dashboard_name}")

                dashboard_body = self.aws_clients.cloudwatch_client.get_dashboard(
                    DashboardName=dashboard_name)["DashboardBody"]

                attributes = {
                    "id": dashboard_name,
                    "dashboard_name": dashboard_name,
                    "dashboard_body": json.dumps(json.loads(dashboard_body), indent=2),
                }

                self.hcl.process_resource(
                    "aws_cloudwatch_dashboard", dashboard_name.replace("-", "_"), attributes)

    def aws_cloudwatch_metric_alarm(self):
        print("Processing CloudWatch Metric Alarms...")

        paginator = self.aws_clients.cloudwatch_client.get_paginator("describe_alarms")
        for page in paginator.paginate(AlarmTypes=["MetricAlarm"]):
            for metric_alarm in page["MetricAlarms"]:
                alarm_name = metric_alarm["AlarmName"]
                print(f"Processing CloudWatch Metric Alarm: {alarm_name}")

                attributes = {
                    "id": alarm_name,
                    "alarm_name": alarm_name,
                    "alarm_description": metric_alarm.get("AlarmDescription", ""),
                    "comparison_operator": metric_alarm["ComparisonOperator"],
                    "evaluation_periods": metric_alarm["EvaluationPeriods"],
                    "metric_name": metric_alarm["MetricName"],
                    "namespace": metric_alarm["Namespace"],
                    "period": metric_alarm["Period"],
                    "statistic": metric_alarm["Statistic"],
                    "threshold": metric_alarm["Threshold"],
                    "actions_enabled": metric_alarm["ActionsEnabled"],
                    "alarm_actions": metric_alarm.get("AlarmActions", []),
                    "insufficient_data_actions": metric_alarm.get("InsufficientDataActions", []),
                    "ok_actions": metric_alarm.get("OKActions", []),
                }

                if "Dimensions" in metric_alarm:
                    attributes["dimensions"] = {
                        dimension["Name"]: dimension["Value"] for dimension in metric_alarm["Dimensions"]}

                self.hcl.process_resource(
                    "aws_cloudwatch_metric_alarm", alarm_name.replace("-", "_"), attributes)

    def aws_cloudwatch_metric_stream(self):
        print("Processing CloudWatch Metric Streams...")

        metric_streams = self.aws_clients.cloudwatch_client.list_metric_streams()[
            "Entries"]
        for metric_stream in metric_streams:
            stream_name = metric_stream["Name"]
            print(f"Processing CloudWatch Metric Stream: {stream_name}")

            attributes = {
                "id": stream_name,
                "name": stream_name,
                "arn": metric_stream["Arn"],
                "firehose_arn": metric_stream["FirehoseArn"],
                # "role_arn": metric_stream["RoleArn"],
                "output_format": metric_stream["OutputFormat"],
            }

            if "IncludeFilters" in metric_stream:
                attributes["include_filters"] = metric_stream["IncludeFilters"]

            if "ExcludeFilters" in metric_stream:
                attributes["exclude_filters"] = metric_stream["ExcludeFilters"]

            self.hcl.process_resource(
                "aws_cloudwatch_metric_stream", stream_name.replace("-", "_"), attributes)
